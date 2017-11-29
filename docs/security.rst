========
Security
========

This page documents aspects of security and how they relate to CALDERA.

Security in CALDERA
===================

While CALDERA has not undergone a formal security review, we have tried to make CALDERA as secure as possible.
Connections between the Server and Agent are encrypted and the Server's identity is cryptographically
authenticated by the Agent using the Server's SSL certificate.

However because of the way that the CALDERA Agents log data, it is possible that the logs may contain sensitive
information discovered during an engagement. To mitigate this possibility we recommend that the Agent Logging
sensitivity be set to *Warning* or *Error* (see :doc:`configuration` for more information on logging levels).

Does CALDERA Contain Malware?
=============================

Most adversaries (and
therefore CALDERA) use tools and features that are built into Windows. However CALDERA does contain some third
party tools that are commonly used by the security community, but may be considered harmful by antivirus software:

 - Invoke-Mimikatz.ps1
 - PowerView.ps1
 - PowerUp.ps1
 - Invoke-ReflectivePEInjection.ps1

Securing the CALDERA Server
===========================

By design, the CALDERA Server is able to execute arbitrary commands on systems that have a CALDERA Agent installed.
Access to the computer running the CALDERA Server as well as the CALDERA Server interface should be protected.

.. warning:: Remember to change the default password to the CALDERA Server.