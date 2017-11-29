================================
Setting up a Network Environment
================================

This section covers how to create a test environment for CALDERA to run in. Although **CALDERA**
is designed to run in real Enterprise environments, it is possible to construct a lab
environment to test CALDERA in.

.. note::  If CALDERA is being installed on a pre-existing network this section can be skipped

In this section we'll also talk specifically about the techniques that adversaries use
within Windows Networks.

Creating a Windows Enterprise Network
-------------------------------------

Windows Enterprise Networks (also called Windows Domains) are common in organizations. They allow network
administrators to easily oversee large amounts of Windows computers, and let computers that are part of the domain
share resources including user accounts, files and printers.

A minimal Windows Enterprise network consists of a Windows Server acting as a Domain Controller and two
Windows Enterprise computers acting as Domain members.

Creating and configuring a Windows Domain is outside the scope of this documentation, but several instructions
exist online for how to configure a Windows Server as a Domain Controller and how to join workstations
to that Domain.

Understanding Credential Overlap
--------------------------------
Many adversarial techniques, and thus those built into CALDERA, require
**credential overlap** in the targeted Windows network.
**Credential overlap** is a condition that's common in Windows Enterprise networks and
involves the following things interacting together:

1. A weakness in Windows that allows an adversary to recover the credentials of all users
   that have logged into a Windows computer since its last reboot
2. A Windows feature that allows users that are administrators to remotely interact
   with Windows computers (for example, to remotely run a process or copy a file)
3. A common issue in real world networks where the same accounts are administrators on
   many (or all) computers in the network
4. A tendency for people to log onto many different computers in the network without rebooting
   (and therefore make it easy to find their passwords in memory)

What all that means is that when an attacker gets on a Windows network, their high
level courses of actions are:

1. Recover the passwords of all the users that have logged onto the system
2. See where those users are administrators
3. Use their administrative privileges to laterally move to new computers
4. See if the attacker’s current level of access accomplishes their goal (compromise a
   specific user, find some kind of documents to exfiltrate, or something else)
5. If their goal is still not accomplished, repeat

Creating a Network with Credential Overlap
------------------------------------------

Believe it or not, in many real networks this strategy is successful. But it
takes some setup to make a test network behave this way. Luckily there are only
a few things you need to do to emulate this kind of situation:

1. Create a domain user account (different from a local user account)
2. Make that user an administrator on both Windows 10 computers in your domain (the account doesn't have to be
   an administrator on the Domain Controller, but it can be)
3. Log the user into one of the Windows 10 computers to place their password in memory

Steps 1 and 2 are permanent changes that only have to be done once whereas Step 3 must
be done any time the computer is rebooted.

Considerations for Windows 8 and Above
--------------------------------------

Windows 8 and above contain some differences from Windows 7. On those systems, several commands must be run
on each computer taking part in the operation to make configuration changes that reflect enterprise networks.

#. Enable Firewall Rules
    Several Firewall rules must be enabled to allow CALDERA techniques to operate correctly. The following commands
    modify the Windows Firewall to allow this traffic

    .. code-block:: console

        powershell -command Enable-NetFirewallRule -DisplayName "'File and Printer Sharing (SMB-In)'"

    .. code-block:: console

        powershell -command Enable-NetFirewallRule -DisplayName "'Remote Scheduled Tasks Management (RPC)'"

#. WDigest caching must be enabled for mimikatz to detect credentials correctly.

    .. code-block:: console

        reg add hklm\SYSTEM\CurrentControlSet\Control\SecurityProviders\WDigest\ /v UseLogonCredential /t REG_DWORD /d 1
