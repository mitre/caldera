Plugin: evals
==========

## APT3 DIY ATT&CK Evaluation Round 1

ATT&CK Evaluations use an Operational Flow to describe the logical ordering to which procedures take place during the evaluation. Round 1's Operational Flow is found [here](https://attackevals.mitre.org/methodology/round1/operational-flow.html).

#### Step 1 - Initial Compromise

The APT3 Eval emulates initial compromise via a malicious executable. Delivery is out of scope for our evaluation, so Step 1 began with a legitimate user executing the payload on the victim host. The malicious executable was a self-extracting archive (SFX) that established persistence and launched an initial callback through a C2 channel.

Step 1 is not in an adversary profile as it requires user execution of the SFX, just as it was done in the actual evaluation. Double-clicking the SFX begins the DIY Evaluation.  
Step 1 tested the following techniques:

##### 1.A.1 - User Execution (T1204) via Scripting (T1064) with PowerShell (T1086)
A legitimate user executes the payload, which launches a batch file that executes CALDERA.

##### 1.B.1 - Registry Run Keys / Start Folder (T1060)
The launched batch file writes a separate batch file (that will also execute CALDERA) to the current user's Startup folder.

##### 1.C.1 - Commonly Used Port (T1043), Standard Application Layer Protocol (T1071)
The executed CALDERA callback ([sandcat.exe](Plugins-sandcat.md)) establishes a C2 channel over HTTP port 8888.

### ATTACK Eval APT 3 Scenario 1 Step 2-3A (Adversary Profile 1)

#### Step 2 - Initial Discovery

The Evals plugin emulates initial discovery using a succession of common discovery commands executed through both the command-line interface and API calls. Discovery techniques in Step 2 sought fundamental knowledge about the system and network required before follow-on activity.	

Step 2 executes the following techniques:

##### 2.A.1 - System Network Configuration Discovery (T1016) via Command-Line Interface (T1059)
The `ipconfig` utility is executed via `cmd` to enumerate local TCP/IP network configuration information.

##### 2.A.2 - System Network Configuration Discovery (T1016) via Command-Line Interface (T1059)
The `arp` utility is executed via `cmd` to enumerate local ARP configuration information.

##### 2.B.1 – System Owner / User Discovery (T1033) via Command-Line Interface (T1059)
The native `echo` command is executed via `cmd` to enumerate local environment variables associated with current user and domain.

##### 2.C.1 – Process Discovery (T1057) via Execution through API (T1106)
This Eval plugin ability uses a modified version of [FuzzySecurity's Get-SystemProcessInformation.ps1](https://github.com/FuzzySecurity/PowerShell-Suite/blob/master/Get-SystemProcessInformation.ps1) script to enumerate local running processes via the Win32 API. This modified version removed the Add-Type functionality by incorporating [Matthew Graeber's PSReflect](https://github.com/mattifestation/PSReflect) functionality, where a .NET type is created using reflection (i.e. csc.exe is never called like with Add-Type).

\*Note there are a number of ways to perform Process Discovery (T1057) via Execution through API (T1106). This Eval plugin ability chose to emulate this step via the NtQuerySystemInformation::SystemProcessInformation API call. However, you can emulate this with other API calls as well (i.e. EnumProcesses, CreateToolhelp32Snapshot, Process32First, Process32Next, WTSEnumerateProcessesA). For more information about performing Process Discovery (T1057) via Execution through API (T1106) [click here](https://docs.microsoft.com/en-us/windows/win32/procthread/process-enumeration).

##### 2.C.2 – Process Discovery (T1057) via Command-Line Interface (T1059)
The `tasklist` utility is executed via `cmd` to enumerate local running processes.

##### 2.D.1 – System Service Discovery (T1007) via Command-Line Interface (T1059)
The `sc` utility is executed via `cmd` to enumerate local active services.

##### 2.D.2 – System Service Discovery (T1007) via Command-Line Interface (T1059)
The `net` utility is executed via `cmd` to enumerate local active services.

##### 2.E.1 – System Information Discovery (T1082) via Command-Line Interface (T1059)
The `systeminfo` utility is executed via `cmd` to enumerate the local operating system configuration.

##### 2.E.2 – System Information Discovery (T1082) via Command-Line Interface (T1059)
The `net` utility is executed via `cmd` to enumerate the local operating system configuration.

##### 2.F.1 – Permissions Groups Discovery (T1069) via Command-Line Interface (T1059)
The `net` utility is executed via `cmd` to enumerate members of the local system's administrators group.

##### 2.F.2 – Permissions Groups Discovery (T1069) via Command-Line Interface (T1059)
The `net` utility is executed via `cmd` to enumerate members of the domain controller’s administrators group.

##### 2.F.3 – Permissions Groups Discovery (T1069) via Command-Line Interface (T1059)
The `net` utility is executed via `cmd` to enumerate members of the domain administrators group.

##### 2.G.1 – Account Discovery (T1087) via Command-Line Interface (T1059)
The `net` utility is executed via `cmd` to enumerate domain user accounts.

##### 2.G.2 – Account Discovery (T1087) via Command-Line Interface (T1059)
The `net` utility is executed via `cmd` to enumerate detailed information about a specific user account.

##### 2.H.1 – Query Registry (T1012) via Command-Line Interface (T1059)
The `reg` utility is executed via `cmd` to enumerate a specific Registry key associated with local system policies to ensure that the user will not be prompted for credentials when elevating permissions.

#### Step 3 - Privilege Escalation

Step 3 tested the following techniques:

##### 3.A.1 - Bypass User Account Control (T1088) via Access Token Manipulation (T1134)
This Eval plugin ability uses [Empire's Invoke-BypassUACTokenManipulation.ps1](https://github.com/EmpireProject/Empire/blob/master/data/module_source/privesc/Invoke-BypassUACTokenManipulation.ps1) script to steal the token of an existing high-integrity process and launch a new, high-integrity CALDERA RAT with limited functionality.

\*Note if a high integrity process is not running the script will attempt to spawn TaskMgr.exe with the RunAs flag. If there is no high integrity process running or TaskMgr.exe fails to spawn as admin the script will fail. We recommend spawning cmd.exe as the high integrity process prior to starting the DIY Eval. Read more about the lab setup [here](https://attackevals.mitre.org/methodology/round1/environment.html).

### Adversary Profile 2 - ATTACK Eval APT 3 Scenario 1 Step 3B-3C

#### Step 3 Continued - Privilege Escalation

The Evals plugin emulates privilege escalation by elevating its' RAT’s process integrity level from medium to high, while maintaining the current user. Step 3 began in the first Adversary Profile with the execution of an Empire Bypass UAC technique. The Bypass UAC technique resulted in a high integrity process that had limited functionality, but allows CALDERA to inject into an already existing high-integrity process, which is not limited in functionality.

Step 3 tested the following techniques:

##### 3.B.1 - Process Discovery (T1057) and 3.C.1 - Process Injection (T1055)
The limited functionality high-integrity RAT injects malicious base64 encoded PowerShell into an existing fully functional high-integrity process, resulting in a new elevated, fully functional high-integrity RAT.

This Eval plugin ability uses [Empire's Invoke-PSInject](https://github.com/EmpireProject/PSInject/blob/master/Invoke-PSInject.ps1) to perform the injection. This  ability added the [EnumProcesses function from Empire's Invoke-BypassUACTokenManipulation.ps1](https://github.com/EmpireProject/Empire/blob/master/data/module_source/privesc/Invoke-BypassUACTokenManipulation.ps1#L876) script in, as it now allows CALDERA to find a high integrity process to inject in to on the fly.

\*Note like Step 3.A if there is no high integrity process running and owned by the current user the script will fail. We recommend spawning cmd.exe as the high integrity process prior to starting the DIY Eval. Read more about the lab setup [here](https://attackevals.mitre.org/methodology/round1/environment.html).

### Adversary Profile 3 - ATTACK Eval APT 3 Scenario 1 Step 4-5A

#### Step 4 - Discovery for Lateral Movement

The Evals plugin emulates a second round of discovery using a sequence of discovery commands executed through the high-integrity process that was injected into during Step 3.C.1. Discovery techniques in Step 4 target knowledge about the system and network specifically related to enabling lateral movement. 

Step 4 tested the following techniques:

##### 4.A.1 - Remote System Discovery (T1018) via Command-Line Interface (T1059)
The `net` utility is executed via `cmd` to enumerate DCs within the domain

##### 4.A.2 - Remote System Discovery (T1018) via Command-Line Interface (T1059)
The `net` utility is executed via `cmd` to enumerate hosts within the domain.

##### 4.B.1 – System Network Configuration Discovery (T1016) via Command-Line Interface (T1059)
The `netsh` utility is executed via `cmd` to enumerate local firewall configuration information.

##### 4.C.1 – System Network Connections Discovery (T1049) via Command-Line Interface (T1059)
The `netstat` utility is executed via `cmd` to enumerate local active network connections.

#### Step 5 - Credential Access

The Evals plugin emulates credential access in a way such that it exposed different formats of legitimate credentials. Step 5 consisted of dumping both plaintext and hashed user passwords, as well as theft of a separate user’s access token.

Step 5 tested the following techniques:

##### 5.A.1 – Credential Dumping (T1003)
This Eval plugin ability uses [Empire's Invoke-Mimikatz](https://raw.githubusercontent.com/EmpireProject/Empire/master/data/module_source/credentials/Invoke-Mimikatz.ps1) script to extract passwords from the memory of lsass via the [sekurlsa::logonpasswords](https://github.com/gentilkiwi/mimikatz/wiki/module-~-sekurlsa) command. 

##### 5.A.2 – Credential Dumping (T1003) using Process Injection (T1055)
This Eval plugin ability uses [Empire's Invoke-Mimikatz](https://raw.githubusercontent.com/EmpireProject/Empire/master/data/module_source/credentials/Invoke-Mimikatz.ps1) script to dump hashes via process injection into LSASS via the [lsadump::sam](https://github.com/gentilkiwi/mimikatz/wiki/module-~-lsadump) command.

### Adversary Profile 4 - ATTACK Eval APT 3 Scenario 1 Step 5B-8A

#### Step 5B - Defense Evasion

##### 5.B.1 – Access Token Manipulation (T1134)
This Eval plugin ability emulates stealing another user's access token and changing the context of the RAT's current thread to that stolen token's security context. The ability impersonates the security context of another logged-on user via the [ImpersonateLoggedOnUser API call](https://docs.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-impersonateloggedonuser). This is done after a call to the [DuplicateTokenEx API call](https://docs.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-duplicatetokenex). Finally, the [RevertToSelf API call](https://docs.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-reverttoself) will terminate the prior impersonation. 

#### Step 6 - Lateral Movement

Step 6 began with discovery targeting the remote host to ensure RDP is enabled.

Step 6 tested the following techniques:

##### 6.A.1 – Query Registry (T1012) via Command-Line Interface (T1059)
The `reg` utility is executed via `cmd` to remotely enumerate a specific Registry key associated with terminal services to ensure RDP is enabled.

\*Note the Evals plugin does not emulate Step 6.B.1 – Commonly Used Port (T1043), Standard Application Layer Protocol (T1071), and Multiband Communication (T1026) and Step 6.C.1 – Remote Desktop Protocol (T1076). This is because the actual lateral movement performed in Round 1 Scenario 1 was done by establishing a Remote Desktop Protocol (RDP) connection to a remote host. Since CALDERA is an automated adversary emulation engine, this would of required additional manual interaction that does not fit in to the CALDERA model at this time.

#### Step 7 - Persistence

The Evals plugin emulates persistence through the creation of a scheduled task on the compromised host.

Step 7 tested the following techniques:

##### 7.C.1 - Scheduled Tasks (T1053) and PowerShell (T1086) via Command-Line Interface (T1059)
The `schtasks` utility is executed via `cmd` to create a scheduled task that executed the CALDERA sandcat payload whenever the user logs in.

\*Note the Evals plugin does not emulate Step 7.A.1 - Create Account (T1136) using Graphical User Interface (T1061) with residual Account Discovery (T1087). This is because during the actual evaluation it was done through the RDP session in Step 6 to the remote host via the GUI Management Console utility `mmc` to add another local user account, including memberships in the local administrators and RDP-enabled groups.

#### Step 8A - Collection

The Evals plugin emulates collection to identify and gather information. Step 8A includes locating files of interest within local and remote file systems.

Step 8A tested the following techniques:

##### 8.A.1 – File and Directory Discovery (T1083) via Command-Line Interface (T1059)
The `dir` command is executed via `cmd` to enumerate files in a pre-mapped drive remote file share.

##### 8.A.2 – File and Directory Discovery (T1083) via Command-Line Interface (T1059)
The `tree` utility is executed via `cmd` to enumerate files in the local filesystem of the initially compromised system.

\*Note the Evals plugin does not emulate Step 8.B.1 – Process Discovery (T1057) via Execution Through API (T1106). This is because during the actual evaluation we needed to perform process discovery to identify explorer.exe's process id as the users keystrokes were collected from the local explorer process.    

\*Note the Evals plugin does not emulate Step 8.C.1 – Input Capture (T1056) via Execution Through API (T1106) with residual Application Window Discovery (T1010). This is because keylogging a user would require additional manual interaction that does not fit in to the CALDERA model at this time.

### Adversary Profile 5 - ATTACK Eval APT 3 Scenario 1 Step 8D-9B

#### Step 8D - Collection

The Evals plugin emulates collection to identify and gather information. Step 8D includes a PowerShell script to harvest a screenshot.

Step 8D tested the following techniques:

##### 8.D.1 – Screen Capture (T1113) via Execution Through API (T1106)
This Eval plugin ability uses [Empire's Get-Screenshot ](https://github.com/EmpireProject/Empire/blob/master/data/module_source/collection/Get-Screenshot.ps1) script to collect a screenshot.

#### Step 9 - Exfiltration

The Evals plugin emulates exfiltration by locating and stealing data. Step 9 begins with the discovery of specific directories of interest followed by exfiltration of a file through the existing C2 channel.

Step 9 tested the following techniques:

##### 9.A.1 – File and Directory Discovery (T1083) via PowerShell (T1086)
PowerShell's built-in alias for the `Get-ChildItem` cmdlet `ls` is used to enumerate files in a remote file share.

##### 9.B.1 – Data from Network Shared Drive (T1039), Exfiltration over C2 Channel (T1041) via PowerShell (T1086)
PowerShell's `Invoke-WebRequest` cmdlet is used to exfil a target file from a remote file share through the existing C2 channel.

### Adversary Profile 6 - ATTACK Eval APT 3 Scenario 1 Step 10

#### Step 10 - Execution of Persistence

The Evals plugin emulates the execution of persistence by triggering previously established persistence mechanisms.

Step 10 tested the following techniques:

##### 10.A.1 – Registry Run Key / Startup Folder (T1060) from 1.B
The batch file (that launches a payload) in the Startup folder is executed when the user logs back in.

##### 10.A.2 – Scheduled Task (T1053) from 7.C
The scheduled task (that launches a payload) is executed when the user logs back in.

\*Note the Evals plugin restarts the machine through PowerShell's `Restart-Computer` cmdlet instead of a manual log out and log back in. This is because within the DetectionLab environment registry keys are modified so that the victim user automatically logs in to the computer. Since CALDERA is an automated adversary emulation engine, it makes more sense to not require additional manual interaction and instead allow CALDERA to initiate the persistence via a computer restart and not a log in/out.

\*Note the Evals plugin does not emulate Step 10.B.1 – Valid Accounts (T1078) using RDP (T1076) from 7.A. This is because Step 7.A would of required additional manual interaction (RDP) that is not utilized at this time.

## Acknowledgements

[PSReflect](https://github.com/mattifestation/PSReflect)      
[PSReflect-Functions](https://github.com/jaredcatkinson/PSReflect-Functions)       
[Get-SystemProcessInformation](https://github.com/FuzzySecurity/PowerShell-Suite/blob/master/Get-SystemProcessInformation.ps1)         
[Get-Screenshot](https://github.com/EmpireProject/Empire/blob/master/data/module_source/collection/Get-Screenshot.ps1)          
[Invoke-BypassUACTokenManipulation](https://github.com/EmpireProject/Empire/blob/master/data/module_source/privesc/Invoke-BypassUACTokenManipulation.ps1)      
[Invoke-PSInject](https://github.com/EmpireProject/PSInject/blob/master/Invoke-PSInject.ps1)      
[Invoke-Mimikatz](https://raw.githubusercontent.com/EmpireProject/Empire/master/data/module_source/credentials/Invoke-Mimikatz.ps1)     
     
[Use PowerShell to Interact with the Windows API: Part 1](https://devblogs.microsoft.com/scripting/use-powershell-to-interact-with-the-windows-api-part-1/)     
[Use PowerShell to Interact with the Windows API: Part 2](https://devblogs.microsoft.com/scripting/use-powershell-to-interact-with-the-windows-api-part-2/)     
[Use PowerShell to Interact with the Windows API: Part 3](https://devblogs.microsoft.com/scripting/use-powershell-to-interact-with-the-windows-api-part-3/)      

[module ~ sekurlsa](https://github.com/gentilkiwi/mimikatz/wiki/module-~-sekurlsa#logonpasswords)     
[module ~ lsadump](https://github.com/gentilkiwi/mimikatz/wiki/module-~-lsadump#sam)      

[DuplicateTokenEx function](https://docs.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-duplicatetokenex)    
[ImpersonateLoggedOnUser function](https://docs.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-impersonateloggedonuser)     
[CreateProcessWithTokenW function](https://docs.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-createprocesswithtokenw)     
[RevertToSelf function](https://docs.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-reverttoself)     
