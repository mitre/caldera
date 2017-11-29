import re
import datetime
import logging
import csv
import io
from .. import util
from typing import List, Dict, NamedTuple
from .errors import *


log = logging.getLogger(__name__)


class powerview(object):
    @staticmethod
    def getnetlocalgroupmember(text: str) -> List[Dict]:
        try:
            users = []
            skip = text.find("ComputerName")
            safe = text[skip:]
            for block in safe.split("\r\n\r\n"):
                lines = block.splitlines()
                parsed_block = {}
                for line in lines:
                    if ':' in line:
                        k, v = line.split(':')
                        parsed_block[k.strip()] = v.strip().lower()
                    else:
                        continue
                # block_dict = {x.strip(): y.strip() for x, y in line.split(':') for line in lines}
                if len(parsed_block):
                    domain, user = parsed_block.get('MemberName').split('\\')
                    users.append(dict(username=user,
                                      is_group=(True if parsed_block.get('IsGroup', '') == "True" else False),
                                      sid=parsed_block.get('SID', ''),
                                      windows_domain=domain, host=parsed_block.get('ComputerName', '')))
            return users
        except:
            raise ParseError("Unexpected Data in return: {}".format(text))

    GetDomainComputerResult = NamedTuple("GetDomainComputerResult", [("dns_hostname", str), ("os_version", Dict)])
    @staticmethod
    def getdomaincomputer(text: str) -> Dict[str, Dict[str, str]]:
        results = dict()

        for block in text.split("\r\n\r\n"):
            if block:
                dns_hostname = None
                parsed_version_info = None
                for line in block.splitlines():
                    if line.startswith("dnshostname"):
                        field_name,  value = [c.strip() for c in line.split(':')]
                        dns_hostname = value.lower()

                    if line.startswith("operatingsystemversion"):
                        value = line.split(":")[-1].strip()  # Looks like: "10.0 (14393)"
                        os_version, build_number = value.split(' ')
                        build_number = build_number[1:-1]  # remove parens
                        major_version, minor_version = os_version.split('.')
                        parsed_version_info = dict(os_name="windows", major_version=major_version, minor_version=minor_version, build_number=build_number)

                    if line.startswith("Exception") and '(0x80005000)' in line:
                        # Domain communication error
                        raise DomainIssueError('Domain Issue 0x80005000: Verify that the rat is running under a '
                                               'Domain Account, and that the Domain Controller can be reached.')

                results[dns_hostname] = dict(parsed_version_info=parsed_version_info)
        return results


class powerup(object):
    @staticmethod
    def get_serviceunquoted(text: str) -> List[Dict]:
        # can take advantage of the bin path to insert new binary upstream (i.e C:\Program.exe)
        services = []
        for block in text.split("\r\n\r\n"):
            service = {}
            lines = block.split("\r\n")
            for i in range(0, len(lines)):
                parts = lines[i].split(":")
                keyword = parts[0].strip()
                if keyword == "ServiceName":
                    service["name"] = parts[1].strip()  # ServiceName : namehere
                elif keyword == "Path":
                    search_line = lines[i]
                    count = 1
                    while "}" not in search_line:  # paths might span multiple lines, fix it
                        search_line += lines[i + count]
                        count += 1
                    regex = re.compile("\\{(.*)\\}")  # ModifiablePath : {C:\Program Files\test.exe}
                    search_line = search_line.replace('                 ', '')
                    log.debug(search_line)
                    path = regex.search(search_line).group(1).strip()
                    service["bin_path"] = path
                elif keyword == "StartName":
                    service["service_start_name"] = parts[1].strip()  # StartName : LocalSystem
                elif keyword == "CanRestart":
                    if parts[1].strip() == "True":
                        service["can_restart"] = True # CanRestart : True
                    else:
                        service["can_restart"] = False
                elif keyword == "ModifiablePath":
                    search_line = lines[i]
                    count = 1
                    while "}" not in search_line:  # paths might span multiple lines, fix it
                        search_line += lines[i + count]
                        count += 1
                    regex = re.compile("\\{(.*)\\}")  # ModifiablePath : {C:\Program.exe, C:\Program Files\test.exe}
                    search_line = search_line.replace('                 ','')
                    log.debug(search_line)
                    paths = regex.search(search_line).group(1).split(',')
                    paths = [path.strip() for path in paths]
                    service["modifiable_paths"] = paths
            if len(service) > 0:
                services.append(service)
        return services

    @staticmethod
    def get_modifiableservicefile(text: str) -> List[Dict]:
        # can replace service binary with a new one
        services = []
        for block in text.split("\r\n\r\n"):
            service = {}
            lines = block.split("\r\n")
            for i in range(0, len(lines)):
                parts = lines[i].split(":")
                keyword = parts[0].strip()
                if keyword == "ServiceName":
                    service["name"] = parts[1].strip() # ServiceName : namehere
                elif keyword == "Path":
                    search_line = lines[i]
                    count = 1
                    while "}" not in search_line:  # paths might span multiple lines, fix it
                        search_line += lines[i + count]
                        count += 1
                    regex = re.compile("\\{(.*)\\}")  # ModifiablePath : {C:\Program Files\test.exe}
                    search_line = search_line.replace('                 ', '')
                    log.debug(search_line)
                    path = regex.search(search_line).group(1).strip()
                    service["bin_path"] = path # full binpath with arguments and everything
                elif keyword == "StartName":
                    service["service_start_name"] = parts[1].strip() # StartName : LocalService
                elif keyword == "CanRestart":
                    if parts[1].strip() == "True":
                        service["can_restart"] = True # CanRestart : True
                    else:
                        service["can_restart"] = False
                elif keyword == "ModifiableFile": # ModifiableFile : {C:\program files\full\path\here.exe}
                    search_line = lines[i]
                    count = 1
                    while "}" not in search_line:  # paths might span multiple lines, fix it
                        search_line += lines[i + count]
                        count += 1
                    regex = re.compile("\\{(.*)\\}")  # ModifiablePath : {C:\Program Files\test.exe}
                    search_line = search_line.replace('                 ', '')
                    log.debug(search_line)
                    path = regex.search(search_line).group(1).strip()
                    service['modifiable_paths'] = [path.strip()]
            if len(service) > 0 and service["name"] != "cagent":
                services.append(service)
        return services

    @staticmethod
    def get_modifiableservice(text: str) -> List[Dict]:
        # can modify a service's binpath to something else (not b/c unquoted or replacing real binary)
        services = []
        for block in text.split("\r\n\r\n"):
            service = {}
            lines = block.split("\r\n")
            for i in range(0, len(lines)):
                parts = lines[i].split(":")
                keyword = parts[0].strip()
                if keyword == "ServiceName":
                    service["name"] = parts[1].strip() # ServiceName : namehere
                elif keyword == "Path":
                    search_line = lines[i]
                    count = 1
                    while "}" not in search_line:  # paths might span multiple lines, fix it
                        search_line += lines[i + count]
                        count += 1
                    regex = re.compile("\\{(.*)\\}")  # ModifiablePath : {C:\Program Files\test.exe}
                    search_line = search_line.replace('                 ', '')
                    log.debug(search_line)
                    path = regex.search(search_line).group(1).strip()
                    service["bin_path"] = path # Path : C:\Program Files\full\path\here.exe
                elif keyword == "StartName":
                    service["service_start_name"] = parts[1].strip() # StartName : LocalSystem
                elif keyword == "CanRestart":
                    if parts[1].strip() == "True":
                        service["can_restart"] = True #CanRestart : True
                    else:
                        service["can_restart"] = False
            if len(service) > 0:
                services.append(service)
        return services

    @staticmethod
    def find_pathdllhijack(text: str) -> List:
        log.debug(text)
        dlls = []
        for block in text.split("\r\n\r\n"):
            for line in block.split("\r\n"):
                parts = line.split(":")
                keyword = parts[0].strip()
                if keyword == "ModifiablePath":
                    dlls.append(':'.join(parts[1:]) + "wlbsctrl.dll")
        return dlls


class net(object):
    @staticmethod
    def time(text: str) -> datetime.datetime:
        if text and len(text) > 0:
            regex = re.compile(r'([0-9]+)/([0-9]+)/([0-9]+) ([0-9]+):([0-9]+):([0-9]+) (A|P)M')
            result = regex.search(text)
            if result is None:
                raise ParseError("Net time output does not look like a time: {}".format(text))
            else:
                try:
                    if result.group(7) == 'P' and result.group(4) != '12':
                        hour = int(result.group(4)) + 12
                    elif result.group(7) == 'A' and result.group(4) == '12':
                        hour = 0
                    else:
                        hour = int(result.group(4))

                    return datetime.datetime(*[int(x) for x in result.group(3, 1, 2)], hour,
                                             *[int(x) for x in result.group(5, 6)])
                except IndexError as e:
                    raise ParseError("Net time output does not look like a time: {}".format(text))

    @staticmethod
    def use(text: str) -> None:
        if text and text.startswith('The command completed successfully'):
            return
        elif text.startswith("System error 1331 has occurred"):
            raise AccountDisabledError
        else:
            raise ParseError("Net use failed: {}".format(text))

    @staticmethod
    def use_delete(text: str) -> None:
        if text:
            if text.strip().endswith('was deleted successfully.'):
                return
            elif text.strip().startswith('The network connection could not be found.'):
                raise NoShareError

        raise ParseError("Net use failed: {}".format(text))


class schtasks(object):
    @staticmethod
    def create(text: str) -> None:
        if text and text.startswith("SUCCESS"):
            return
        else:
            raise ParseError("unknown error with schtasks: {}".format(text))

    @staticmethod
    def delete(text: str) -> None:
        if text and text.startswith("SUCCESS"):
            return
        else:
            raise ParseError("unknown error with schtasks: {}".format(text))


class cmd(object):
    @staticmethod
    def copy(text: str) -> None:
        if text and len(text) > 0 and text.startswith('The system cannot find the file specified.'):
            raise ParseError("unable to perform copy.")
        elif text and len(text) > 0 and text.strip().startswith('1 file(s) copied.'):
            return
        elif text and len(text) > 0 and 'The process cannot access the file because it is being used by another process.' in text:
            raise FileInUseError
        else:
            raise ParseError("Unknown output of copy: {}".format(text))

    @staticmethod
    def delete(text: str) -> None:
        text = text.strip()
        if not text:
            return

        elif text.startswith('Could Not Find'):
            raise NoFileError
        elif text.endswith('Access is denied.'):
            raise AccessDeniedError
        elif text.startswith('The network path was not found.'):
            raise NoNetworkPathError
        elif text.startswith('The filename, directory name, or volume label syntax is incorrect.'):
            raise PathSyntaxError
        else:
            raise ParseError("Unknown output of delete: {}".format(text))

    @staticmethod
    def move(text: str) -> None:
        if "cannot find the file" in text:
            raise NoFileError
        elif "Access is denied" in text:
            raise AccessDeniedError
        elif "1 file(s) moved" in text:
            return
        else:
            raise ParseError("Unknown output of move: {}".format(text))

    @staticmethod
    def dir_collect(text: str) -> List[str]:
        matches = []
        if "File Not Found" in text: # this also happens when access is denied, it's the same error
            raise FileNotFoundError
        elif "FAILED" in text:
            raise ParseError("Failed to handle a parse case: {}".format(text))
        for match in text.split("\r\n")[:-1]:
            matches.append(match.strip())
        return matches

    @staticmethod
    def powershell(text: str) -> None:
        if "it does not exist" in text:
            raise FileNotFoundError
        elif "Access to the path" in text and "is denied" in text:
            raise AccessDeniedError
        else:
            return


class nbtstat(object):
    @staticmethod
    def n(text: str) -> str:
        if text and len(text) > 0:
            regex = re.compile(r'\s*(\S+)\s*<[0-9][0-9]>\s*GROUP')
            result = regex.search(text)
            if result is None:
                raise ParseError("Result is not well formed: {}".format(text))
            else:
                try:
                    return result.group(1).lower()
                except IndexError:
                    raise ParseError("Net time output does not look like a time: {}".format(text))


class wmic(object):
    @staticmethod
    def create(text: str) -> None:
        if text and len(text) > 0:
            lines = [x for x in text.splitlines() if x]
            if len(lines) > 1 and lines[0] == "Executing (Win32_Process)->Create()" and \
                    lines[1] == "Method execution successful.":
                return
        raise ParseError("Unknown output of wmic create: {}".format(text))


class taskkill(object):
    @staticmethod
    def taskkill(text: str) -> None:
        text = text.strip()
        if text.startswith("SUCCESS"):
            return
        elif text.startswith('ERROR: The process') and text.endswith("not found."):
            raise NoProcessError
        else:
            raise ParseError("Unknown output of taskkill: {}".format(text))


class shutdown(object):
    @staticmethod
    def shutdown(text: str) -> None:
        text = text.strip()
        if not text:
            return
        elif "Access Denied" in text:
            raise AccessDeniedError
        else:
            raise ParseError("Unknown output of shutdown")


class psexec(object):
    @staticmethod
    def copy(text: str):
        if "started on" in text:
            return True
        elif "being used by another process" in text:
            raise ParseError("PSEXEC in use error")
        else:
            raise ParseError("Unknown PSEXEC error")


class sc(object):
    @staticmethod
    def create(text: str) -> None:
        if "SUCCESS" in text:
            return
        else:
            raise ParseError("Unknown output of sc create: {}".format(text))

    @staticmethod
    def delete(text: str) -> None:
        if "SUCCESS" in text:
            return
        elif "FAILED 5" in text:
            raise AccessDeniedError('Access denied to delete service {}'.format(text))
        elif "FAILED 1060" in text:
            raise NoServiceError('sc tried to delete a non-existent service {}'.format(text))
        else:
            raise ParseError('Unknown output of sc delete: {}'.format(text))

    @staticmethod
    def query(text: str) -> Dict:
        service = {}
        if "FAILED 1060" in text:
            raise NoServiceError("The service does not exist")
        for line in text.split("\r\n"):
            parts = line.split(":")
            if parts[0].strip() == "STATE":
                service['state'] = parts[1].split()[1]
        return service

    @staticmethod
    def start(text: str) -> None:
        if "FAILED 1053" in text:
            raise UnresponsiveServiceError('Service did not respond to start: {}'.format(text))
        elif "START_PENDING" in text:
            return
        elif "FAILED 1056" in text:
            raise ServiceAlreadyRunningError()
        else:
            raise ParseError('Unknown output of sc start: {}'.format(text))

    @staticmethod
    def stop(text: str) -> None:
        if "FAILED 5" in text:
            raise AccessDeniedError('Access denied to stop service')
        elif "SUCCESS" in text:
            return
        elif "FAILED 1062" in text:
            raise ServiceNotStartedError
        elif "STOP_PENDING" in text:
            return
        elif "FAILED 1061" in text:
            raise CantControlServiceError
        elif "FAILED 1060:" in text:
            raise NoServiceError
        else:
            raise ParseError('Unknown output of sc stop: {}'.format(text))

    @staticmethod
    def config(text: str) -> None:
        if "SUCCESS" in text:
            return
        elif "FAILED 1060" in text:
            raise NoServiceError('sc tried to config a non-existent service {}'.format(text))
        elif "FAILED 5" in text:
            raise AccessDeniedError('Access denied to config service')
        elif "USAGE:" in text:
            raise ParseError('Invalid config string: {}'.format(text))
        else:
            raise ParseError('Unknown output of sc config: {}'.format(text))


class timestomp(object):
    @staticmethod
    def timestomp(output: str) -> Dict:
        """
        Parses output of the timestomping command. Returns a dictionary containing
        the timestomped file's creation time, last access time, last write time,
        along with a boolean indicating whether timestomping actually occurred.
        Also now contains an entry indicating the file that the timestomp function
        took timestamps from.
        """
        info_dict = {}
        pruned_dict = {}
        important_keys = ["TimestampModified", "TimestompedWith", "CreationTime", "LastAccessTime", "LastWriteTime",
                          "OldCreationTime", "OldAccessTime", "OldWriteTime"]

        # Another form of searching - compare vs. parse_mimikatz_process for relative speed?

        lines = output.splitlines()
        for line in lines:
            m = re.match(r"(\w*)\s*:\s(.*)", line)
            if m is not None and m.groups()[0] is not None and m.groups()[1].strip() is not "":
                info_dict[m.groups()[0]] = m.groups()[1]

        for curr_key in important_keys:
            if curr_key in info_dict:
                pruned_dict[curr_key] = info_dict[curr_key]

        return pruned_dict


class mimikatz(object):
    @staticmethod
    def sekurlsa_pth(output: str) -> Dict:
        """
        Parses mimikatz output with the pth command and returns a dictionary containing
        the process PID and TID, as well as the process executed
        Args:
            output: stdout of "mimikatz.exe privilege::debug sekurlsa::pth [arguments] exit"
        Returns:
            A dictionary with keys: 'Username', 'Password', 'Domain', 'Hash'
        """
        masked_process = {}

        if 'ERROR kuhl_m_sekurlsa_acquireLSA' in output:
            raise AcquireLSAError

        if 'This script contains malicious content and has been blocked by your antivirus software.' in output:
            raise AVBlockError

        # A simple set of regex commands to get the program name, PID, and TID
        program = re.search(r"^\s*program\s*:\s*([^\r\n]*)", output, flags=re.MULTILINE)
        pid = re.search(r"^\s*\|\s*PID\s*(\d*)", output, flags=re.MULTILINE)
        tid = re.search(r"^\s*\|\s*TID\s*(\d*)", output, flags=re.MULTILINE)
        user = re.search(r"^\s*user\s*:\s*([^\r\n]*)", output, flags=re.MULTILINE)
        domain = re.search(r"^\s*domain\s*:\s*([^\r\n]*)", output, flags=re.MULTILINE)

        if program is not None and program.groups()[0] is not None:
            masked_process["program"] = program.groups()[0]
        else:
            raise ParseError('Could not find exploited process. This probably indicates a parser bug')

        if pid is not None and pid.groups()[0] is not None:
            masked_process["pid"] = pid.groups()[0]
        else:
            raise ParseError('Could not find process pid. This probably indicates a parser bug')

        if tid is not None and tid.groups()[0] is not None:
            masked_process["tid"] = tid.groups()[0]
        else:
            raise ParseError('Could not find thread tid. This probably indicates a parser bug')

        if user is not None and user.groups()[0] is not None:
            masked_process["user"] = user.groups()[0]
        else:
            raise ParseError('Could not find user. This probably indicates a parser bug')

        if domain is not None and domain.groups()[0] is not None:
            masked_process["domain"] = domain.groups()[0]
        else:
            raise ParseError('Could not find domain. This probably indicates a parser bug')

        return masked_process

    @staticmethod
    def sekurlsa_logonpasswords(output: str) -> List[Dict]:
        """
        Parses mimikatz output with the logonpasswords command and returns a list of dicts of the credentials.
        Args:
            output: stdout of "mimikatz.exe privilege::debug sekurlsa::wdigest exit"
        Returns:
            A list of dictionaries where each dict is a credential, with keys: 'Username', 'Password', 'Domain', 'Hash'
        """
        # split sections using "Authentication Id" as separator
        sections = output.split("Authentication Id")
        creds = []

        # the header for the packages that contain plaintext user credentials
        ssp = ['tspkg :', 'wdigest :']
        packages = {}
        for section in sections[1:]:
            package = {}
            package_name = ""
            in_header = True
            for line in section.splitlines():
                line = line.strip()
                if in_header:
                    if line.startswith('msv'):
                        in_header = False
                    else:
                        continue

                if line.startswith('['):
                    pass
                elif line.startswith('*'):
                    m = re.match(r"\s*\* (.*?)\s*: (.*)", line)
                    if m:
                        package[m.group(1)] = m.group(2)

                elif line:
                    # parse out the new section name
                    match_group = re.match(r"([a-z]+) :", line)
                    if match_group:
                        # this is the start of a new ssp
                        # save the current ssp if necessary
                        if 'Username' in package and package['Username'] != '(null)' and \
                                (('Password' in package and package['Password'] != '(null)') or 'NTLM' in package):
                            packages[package_name] = package

                        # reset the package
                        package = {}

                        # get the new name
                        package_name = match_group.group(1)

            # save this section
            if packages:
                creds.append(packages)
                packages = {}

        return creds

    @classmethod
    def sekurlsa_logonpasswords_condensed(cls, output: str) -> List[Dict]:
        """
        Parses mimikatz output with the logonpasswords command and returns a list of dicts of the credentials.
        Args:
            output: stdout of "mimikatz.exe privilege::debug sekurlsa::wdigest exit"
        Returns:
            A list of dictionaries where each dict is a credential, with keys: 'Username', 'Password', 'Domain',
            'NLTM', and 'SHA1'
        """
        accounts = cls.sekurlsa_logonpasswords(output)

        # remove all the weird SSPs
        accounts = [{k: v for k, v in x.items() if k in ('msv', 'tspkg', 'wdigest')} for x in accounts]

        # invert
        flattened = []
        for account in accounts:
            compressed = {}
            for package in account.values():
                for key, val in package.items():
                    if key in compressed and compressed[key] != val:
                        raise ParseError
                    compressed[key] = val
            flattened.append(compressed)

        # remove computer account
        flattened = [x for x in flattened if x and 'Username' in x and not x['Username'].endswith('$')]
        return util.unique_list_of_dicts(flattened)


class reg(object):
    WinRegValue = NamedTuple(typename="WinRegValue", fields=[("name", str), ("type", str), ("data", str)])

    @staticmethod
    def query(text: str) -> Dict[str, Dict[str, WinRegValue]]:
        if "The system was unable to find the specified registry key or value" in text:
            raise NoRegKeyError
        elif "ERROR" in text:
            raise ParseError("reg query command returned an ERROR: {}".format(text))

        res = {}
        current_key = None
        for line in text.split("\r\n"):
            if not line:
                continue  # skip empty string
            elif line.startswith("    ") and current_key and len(line.split()) == 3:  # Data -- ignore empty defaults
                v_name, v_type, v_data = line.split()
                res[current_key][v_name] = reg.WinRegValue(name=v_name, type=v_type, data=v_data)
            elif line.startswith("HK"):  # New key
                current_key = line
                res[current_key] = {}
        return res

    @staticmethod
    def add(text: str) -> None:
        if "The system was unable to find the specified registry key or value" in text:
            raise NoRegKeyError
        elif "ERROR: Invalid key name." in text:
            raise NoRegKeyError
        elif "ERROR: The parameter is incorrect." in text:
            raise IncorrectParameterError
        elif "ERROR" in text:
            raise ParseError

        return

    @staticmethod
    def load(text: str) -> None:
        if "ERROR: Access is denied." in text.strip():
            raise AccessDeniedError
        elif "ERROR: The process cannot access the file because it is being used by another process." in text.strip():
            raise FileInUseError
        elif "ERROR" in text:
            raise ParseError

        return

    @staticmethod
    def unload(text: str) -> None:
        if "ERROR" in text:
            raise ParseError

        return

    @staticmethod
    def delete(text: str) -> None:
        if "Invalid key name" in text or 'The system was unable to find the specified registry key or value' in text:
            raise NoRegKeyError
        elif "ERROR" in text:
            raise ParseError

        return


class systeminfo(object):
    @staticmethod
    def csv_with_headers(text: str) -> Dict:
        """ Return a Dict with systeminfo fields: values. Also, add original stdout text to the dict before returning.
        Could also store this info in a custom object or NamedTuple, but this is fewer lines."""
        if text.startswith("ERROR"):
            raise ParseError("Error encountered running systeminfo: {}".format(text))
        try:
            keys, values = csv_to_list(text)
            res = {keys[i]: values[i] for i in range(len(keys))}
            res['_original_text'] = text

            # parse out version info and add as dict
            version_string = res['OS Version'].split(' ')[0]
            major_version, minor_version, build_number = [int(n) for n in version_string.split('.')]

            # The keys in the dict below are named for easy unpacking into ObservedOSVersion database objects
            res['parsed_version_info'] = dict(os_name="windows", major_version=major_version,
                                              minor_version=minor_version, build_number=build_number)
            return res
        except:
            raise ParseError("Error encountered while trying to parse systeminfo output: {}".format(text))


class tasklist(object):
    _fix_name = {"Image Name": "image_name",
                 "PID": "pid",
                 "Session Name": "session_name",
                 "Session#": "session_number",
                 "Mem Usage": "mem_usage",
                 "Status": "status",
                 "User Name": "username",
                 "CPU Time": "cpu_time",
                 "Window Title": "window_title",
                 "Services": "services",
                 "Modules": "modules"}

    @staticmethod
    def csv_with_headers(text: str) -> List:
        rows = csv_to_list(text)
        headers = rows.pop(0)

        # Fix headers so that they correspond to field names in objects.ObservedProcess
        for idx, field_name in enumerate(headers):
            headers[idx] = tasklist._fix_name[field_name]

        # Convert PID and Session# to be integers
        for row in rows:
            for index, field in enumerate(row):
                if field.isdigit():
                    row[index] = int(field)

        return [dict(zip(headers, row)) for row in rows]


def csv_to_list(text: str) -> List[List]:
    """
    Converts CSV formatted output from Windows utilities into a list.
    :param text: CSV formatted text output from a Windows utility (e.g. "/FO CSV" )
    :return: A List of lists like so [[r1c1, r1c2, r1c3, ...], [r2c1, r2c2, r2c3, ...] ...]
    """
    return list(csv.reader(io.StringIO(text), delimiter=',', quotechar='"'))

