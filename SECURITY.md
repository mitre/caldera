This repository contains two externally produced pieces of software that can be 
classified as pen-testing, security testing tools.

1. Mimikatz
2. PowerView

## Mimikatz 

Generally speaking, mimikatz has many features, primarily revolving around 
extracting, manipulating, and using Windows credentials. It can do this in many
ways. The most common method is by directly accessing and decrypting the memory 
of the Windows Local Security Authority Sub System, lsass.exe. By doing this 
it is able to get plaintext credentials from a live Windows systems. Most other 
credential access methods are only able to recover hashed credentials (which 
are still extremely useful). Mimikatz is [open source](https://github.com/gentilkiwi/mimikatz), 
its [methods](http://www.nosuchcon.org/talks/2014/D2_02_Benjamin_Delpy_Mimikatz.pdf) 
as well as [detection and mitigation mechanisms](https://jimshaver.net/2016/02/14/defending-against-mimikatz/)
have been presented on. It has also been [incorporated into the Metasploit Framework](https://www.offensive-security.com/metasploit-unleashed/mimikatz/).

This repository contains compiled versions of mimikatz in both .ps1 and .dll
form. These programs have been base64 encoded and are stored in python source 
files:
- caldera\caldera\files\mimi32-dll
- caldera\caldera\files\mimi64-dll
- caldera\caldera\invoke-mimi-ps1

CALDERA uses Mimikatz to decrypt Windows passwords from the memory of 
the lsass.exe process on Windows.

## PowerView

PowerView is a PowerShell script that is used for Network Enumeration. It is
open source software contained within the [PowerSploit framework](https://github.com/PowerShellMafia/PowerSploit/blob/master/Recon/PowerView.ps1).
PowerView uses Windows [Active Directory Services Interface (ADSI)](https://msdn.microsoft.com/en-us/library/aa772170(v=vs.85).aspx)
and [LDAP](https://msdn.microsoft.com/en-us/library/aa367008(v=vs.85).aspx) to
query information from the Window's Domains Active Directory server about the 
domain. 

This repository contains PowerView:
 - caldera\caldera\files\powerview-ps1

CALDERA uses PowerView to query the Active Directory server. It collects:
host and domain names of the computers in the domain, user account names, 
Administrator account names, and the Windows Domain name of the domain.