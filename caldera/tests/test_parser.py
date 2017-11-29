from unittest import TestCase
import datetime

from caldera.tests import parser_tests_data as examples
from caldera.app.commands import parsers


class TestParser(TestCase):
    def testGetDomainComputer(self):
        t = examples.powerview_GetDomainComputer

        expected = {"win10x02.mountainpeak.local": {"parsed_version_info": dict(major_version='10',
                                                                              os_name='windows',
                                                                              minor_version='0',
                                                                              build_number='15063')},
                    "win10x01.mountainpeak.local": {"parsed_version_info": dict(major_version='10',
                                                                              os_name='windows',
                                                                              minor_version='0',
                                                                              build_number='15063')},
                    "win2016xdc.mountainpeak.local": {"parsed_version_info": dict(major_version='10',
                                                                                os_name='windows',
                                                                                minor_version='0',
                                                                                build_number='14393')},
                    "win81x01.mountainpeak.local": {"parsed_version_info": dict(major_version='6',
                                                                              os_name='windows',
                                                                              minor_version='3',
                                                                              build_number='9600')}}
        self.maxDiff = None
        self.assertEqual(parsers.powerview.getdomaincomputer(t), expected)

    def testNbtstat(self):
        t = examples.nbtstat
        self.assertEqual(parsers.nbtstat.n(t), "caldera")

    def testGetNetLocalGroupMember(self):
        t = examples.powerview_GetNetLocalGroupMember
        expected = [{'host': 'win81x01', 'is_group': False, 'sid': 's-1-5-21-2011530082-2021195812-4237720560-500',
                     'username': 'administrator', 'windows_domain': 'win81x01'},
                    {'host': 'win81x01', 'is_group': False, 'sid': 's-1-5-21-2011530082-2021195812-4237720560-1001',
                     'username': 'vagrant', 'windows_domain': 'win81x01'},
                    {'host': 'win81x01', 'is_group': False, 'sid': 's-1-5-21-2011530082-2021195812-4237720560-1003',
                     'username': 'sshd_server', 'windows_domain': 'win81x01'},
                    {'host': 'win81x01', 'is_group': False, 'sid': 's-1-5-21-1876816822-289827840-578243815-512',
                     'username': 'domain admins', 'windows_domain': 'mountainpeak'},
                    {'host': 'win81x01', 'is_group': False, 'sid': 's-1-5-21-1876816822-289827840-578243815-1108',
                     'username': 'helpdesk', 'windows_domain': 'mountainpeak'}]

        self.assertCountEqual(parsers.powerview.getnetlocalgroupmember(t), expected)

    def testNetUse(self):
        t = "The command completed successfully."
        self.assertEqual(parsers.net.use(t), None)

        t = "System error 1331 has occurred.\r\n\r\nThis user can't sign in because this account is currently disabled.\r\n\r\n"
        with self.assertRaises(parsers.AccountDisabledError):
            parsers.net.use(t)

    def testNetTime(self):
        t = """Current time at \\test.pc is 2/6/2017 6:25:49 PM

The command completed successfully."""
        self.assertEqual(parsers.net.time(t), datetime.datetime(2017, 2, 6, 18, 25, 49))

        t = """Current time at \\test.pc is 12/16/2017 6:25:49 AM

        The command completed successfully."""
        self.assertEqual(parsers.net.time(t), datetime.datetime(2017, 12, 16, 6, 25, 49))

    def testNetUseDelete(self):
        t = """\\\\win8x02.mountainpeak.local\\C$ was deleted successfully.\r\n\r\n"""

        self.assertEqual(parsers.net.use_delete(t), None)

        t = """The network connection could not be found.\r\n\r\nMore help is available by typing NET HELPMSG 2250.\r\n\r\n"""
        with self.assertRaises(parsers.NoShareError):
            parsers.net.use_delete(t)

    def testSchtasksCreate(self):
        t = "SUCCESS: The scheduled task \"caldera4eva\" has successfully been created.\r\n"
        self.assertEqual(parsers.schtasks.create(t), None)

    def testSchtasksDelete(self):
        t = "SUCCESS: The scheduled task \"caldera4eva\" was successfully deleted.\r\n"
        self.assertEqual(parsers.schtasks.delete(t), None)

    def testCopy(self):
        t = "        1 file(s) copied.\r\n"
        self.assertEqual(parsers.cmd.copy(t), None)

        t = "The process cannot access the file because it is being used by another process.\r\n"
        with self.assertRaises(parsers.FileInUseError):
            parsers.cmd.copy(t)

    def testWmicCreate(self):
        t = examples.wmic_create
        self.assertEqual(parsers.wmic.create(t), None)

    def testTaskkill(self):
        t = "SUCCESS: The process with PID 3692 has been terminated.\r\n"
        self.assertEqual(parsers.taskkill.taskkill(t), None)

        t = "ERROR: The process \"384\" not found.\r\n"
        with self.assertRaises(parsers.NoProcessError):
            parsers.taskkill.taskkill(t)

    def testDelete(self):
        t = "Could Not Find C:\\windows\\system32\\test\r\n"
        with self.assertRaises(parsers.NoFileError):
            parsers.cmd.delete(t)

        t = "C:\\commander.exe\r\nAccess is denied.\r\n"
        with self.assertRaises(parsers.AccessDeniedError):
            parsers.cmd.delete(t)

        t = "The network path was not found.\r\n"
        with self.assertRaises(parsers.NoNetworkPathError):
            parsers.cmd.delete(t)

        t = "The filename, directory name, or volume label syntax is incorrect.\r\n"
        with self.assertRaises(parsers.PathSyntaxError):
            parsers.cmd.delete(t)

        t = "\r\n"
        self.assertEqual(parsers.cmd.delete(t), None)

    def testScCreate(self):
        t = "[SC] CreateService SUCCESS\r\n"
        self.assertEqual(parsers.sc.create(t), None)

    def testScDelete(self):
        t = "[SC] DeleteService SUCCESS\r\n"
        self.assertEqual(parsers.sc.delete(t), None)

    def testMimikatz(self):
        t = examples.mimi_logonpasswords3
        result = parsers.mimikatz.sekurlsa_logonpasswords_condensed(t)
        self.assertCountEqual(result, [{'Password': 'P@ssw0rd',
                                   'Username': 'helpdesk01',
                                   'LM': '921988ba001dc8e14a3b108f3fa6cb6d',
                                   'SHA1': '9131834cf4378828626b1beccaa5dea2c46f9b63',
                                   'NTLM': 'e19ccf75ee54e06b06a5907af13cef42',
                                   'Domain': 'MOUNTAINPEAK'}])

    def testMimikatz2(self):
        t = examples.mimi_logonpasswords4
        result = parsers.mimikatz.sekurlsa_logonpasswords_condensed(t)
        self.assertCountEqual(result, [{'LM': '921988ba001dc8e14a3b108f3fa6cb6d',
                                   'NTLM': 'e19ccf75ee54e06b06a5907af13cef42',
                                   'Domain': 'MOUNTAINPEAK',
                                   'SHA1': '9131834cf4378828626b1beccaa5dea2c46f9b63',
                                   'Username': 'domainad',
                                   'Password': 'P@ssw0rd'},
                                  {'LM': '921988ba001dc8e14a3b108f3fa6cb6d',
                                   'NTLM': 'e19ccf75ee54e06b06a5907af13cef42',
                                   'Domain': 'MOUNTAINPEAK',
                                   'SHA1': '9131834cf4378828626b1beccaa5dea2c46f9b63',
                                   'Username': 'helpdesk01',
                                   'Password': 'P@ssw0rd'}])

    # Tests sekurlsa_pth
    def testPTH(self):
        t = examples.mimi_pth1
        result = parsers.mimikatz.sekurlsa_pth(t)
        self.assertEqual(result, {'domain': 'mountainpeak',
                                  'user': 'helpdesk01',
                                  'program': 'sc.exe \\\\win7x04.mountainpeak.local start caldera',
                                  'pid': '1140',
                                  'tid': '976'})

    # Tests sekurlsa_pth error
    def testPTHAcquireLSAError(self):
        t = examples.mimi_pth2
        with self.assertRaises(parsers.AcquireLSAError):
            parsers.mimikatz.sekurlsa_pth(t)

    def testPTH_AVError(self):
        t = examples.mimi_pth3
        with self.assertRaises(parsers.AVBlockError):
            parsers.mimikatz.sekurlsa_pth(t)

    def testTimestomp(self):
        t = examples.timestomp
        result = parsers.timestomp.timestomp(t)
        self.assertEqual(result, {'CreationTime': '6/23/2017 10:11:53 AM', 'LastAccessTime': '6/23/2017 10:11:53 AM',
                                  'LastWriteTime': '5/31/2017 10:06:59 AM', 'TimestampModified': 'True',
                                  'TimestompedWith': 'C:\\Users\\bob\\Documents\\Empty\\stuff.txt',
                                  'OldCreationTime': '06/21/2017 11:06:12',
                                  'OldAccessTime': '06/21/2017 11:06:12', 'OldWriteTime': '04/27/2017 20:34:21'})

    def testRegQuery(self):
        t = "ERROR: The system was unable to find the specified registry key or value.\r\n"
        with self.assertRaises(parsers.NoRegKeyError):
            parsers.reg.query(t)

        t = examples.reg_query
        parsers.reg.query(t)

    def testRegAdd(self):
        t = "The operation completed successfully.\r\n\r\n"
        self.assertEqual(parsers.reg.add(t), None)

        t = "ERROR: Invalid key name.\r\nType \"REG ADD \/?\" for usage.\r\n"
        with self.assertRaises(parsers.NoRegKeyError):
            parsers.reg.add(t)

        t = "ERROR: The parameter is incorrect.\r\n"
        with self.assertRaises(parsers.IncorrectParameterError):
            parsers.reg.add(t)

    def testRegLoad(self):
        t = "The operation completed successfully.\r\n\r\n"
        self.assertEqual(parsers.reg.load(t), None)

        t = "ERROR: Access is denied.\r\n"
        with self.assertRaises(parsers.AccessDeniedError):
            parsers.reg.load(t)

        t = "ERROR: The process cannot access the file because it is being used by another process.\r\n"
        with self.assertRaises(parsers.FileInUseError):
            parsers.reg.load(t)

    def testRegUnload(self):
        t = "The operation completed successfully.\r\n\r\n"
        self.assertEqual(parsers.reg.unload(t), None)

    def testUnquotedServicePaths(self):
        t = examples.service_paths
        self.assertEqual(parsers.powerup.get_serviceunquoted(t), [{'name': 'testservice',
                                                                   'bin_path': 'C:\\Users\\bob\My Documents\\space here\\whatever.exe',
                                                                   'service_start_name': 'LocalSystem',
                                                                   'can_restart': True,
                                                                   'modifiable_paths': ['C:\\Users\\bob\\My.exe',
                                                                                        'C:\\Users\\bob\\My Documents\\space.exe',
                                                                                        'C:\\Users\\bob\\My Documents\\space here\\whatever.exe']}])

    def testServicePermissions(self):
        t = examples.service_permissions
        self.assertEqual(parsers.powerup.get_modifiableservice(t), [{'name': 'testservice',
                                                                     'bin_path': 'C:\\Users\\bob\\My Documents\\space here\\whatever.exe',
                                                                     'service_start_name': 'LocalSystem',
                                                                     'can_restart': True}])

    def testServiceFilePermission(self):
        t = examples.service_file_permissions
        self.assertEqual(parsers.powerup.get_modifiableservicefile(t), [{'name': 'testservice',
                                                                         'bin_path': 'C:\\Users\\bob\\My Documents\\space here\\whatever.exe',
                                                                         'service_start_name': 'LocalSystem',
                                                                         'can_restart': True,
                                                                         'modifiable_paths': [
                                                                             'C:\\Users\\bob\\My Documents\\space here\\whatever.exe']}])

    def testTasklistVerbose(self):
        t = examples.tasklist_csv_verbose
        x = parsers.tasklist.csv_with_headers(t)
        self.assertEqual({'image_name': 'System Idle Process', 'pid': 0, 'session_name': 'Services',
                          'session_number': 0, 'mem_usage': '24 K', 'status': 'Unknown',
                          'username': 'NT AUTHORITY\SYSTEM', 'cpu_time': '2:35:45', 'window_title': 'N/A'},
                         x[0])

        self.assertEqual({'image_name': 'VBoxService.exe', 'pid': 688, 'session_name': 'Services',
                          'session_number': 0, 'mem_usage': '2,764 K', 'status': 'Unknown',
                          'username': 'N/A', 'cpu_time': '0:00:00', 'window_title': 'N/A'},
                         x[-1])

        # when run with /s, the output is missing the "Window Title" and "Status" column
        t = examples.tasklist_system_csv_verbose
        x = parsers.tasklist.csv_with_headers(t)
        self.assertEqual({'image_name': 'System Idle Process', 'pid': 0, 'session_name': '',
                          'session_number': 0, 'mem_usage': '24 K', 'username': 'N/A', 'cpu_time': '3:06:17'},
                         x[0])

    def testTasklistSvc(self):
        t = examples.tasklist_service_csv
        x = parsers.tasklist.csv_with_headers(t)
        self.assertEqual({'image_name': 'smss.exe', 'pid': 284, 'services': 'N/A'}, x[2])
        self.assertEqual({'image_name': 'svchost.exe', 'pid': 804, 'services': 'AudioSrv,Dhcp,eventlog,lmhosts,wscsvc'},
                         x[-1])

    def testTasklistModules(self):
        t = examples.tasklist_modules_csv

        x = parsers.tasklist.csv_with_headers(t)
        self.assertEqual(x[1], {'image_name': 'System', 'pid': 4, 'modules': 'N/A'})
        self.assertEqual({'image_name': 'taskhost.exe', 'pid': 1824,
                          'modules': 'ntdll.dll,kernel32.dll,KERNELBASE.dll,msvcrt.dll,ole32.dll,GDI32.dll,USER32.dll,LPK.dll,USP10.dll,RPCRT4.dll,OLEAUT32.dll,IMM32.DLL,MSCTF.dll,CRYPTBASE.dll,sechost.dll,ADVAPI32.dll,uxtheme.dll,dwmapi.dll,CLBCatQ.DLL,PlaySndSrv.dll,RpcRtRemote.dll,HotStartUserAgent.dll,dimsjob.dll,SHLWAPI.dll,MsCtfMonitor.dll,MSUTB.dll,WINSTA.dll,WTSAPI32.dll,slc.dll,taskschd.dll,SspiCli.dll,netprofm.dll,NSI.dll,nlaapi.dll,CRYPTSP.dll,rsaenh.dll,npmproxy.dll,CRYPT32.dll,MSASN1.dll,dsrole.dll,WINMM.dll'},
                         x[-1])

    def testSystemInfoLocal(self):
        t = examples.systeminfo_local

        x = parsers.systeminfo.csv_with_headers(t)
        self.assertEqual('WIN-703', x['Host Name'])
        self.assertEqual('Microsoft Windows 7 Enterprise ', x['OS Name'])
        self.assertEqual('Microsoft Corporation', x['OS Manufacturer'])

    def testDirListCollect(self):
        t = examples.dirlist_collect

        files = parsers.cmd.dir_collect(t)
        self.assertEqual(files, ["C:\\Users\\admin\\Contacts\\admin.contact",
                                 "C:\\Users\\All Users\\Microsoft\\User Account Pictures\\admin.dat"])
