============
Requirements
============

Operating System Requirements
-----------------------------
**CALDERA** has both a Server and an Agent, the requirements for each are different.

The agent is installed on each computer that will be involved in the emulation exercise. The agent
supports **64 bit versions of Windows 7** and higher.

The server must be installed on a computer that is accessible over the network to all agents.
Both **Windows** and **Linux** are supported.

See :doc:`installation` for information on installing the Server and Agents.

Network Requirements
--------------------

CALDERA operates in a Windows Enterprise network environment.
At a minimum this will contain a Domain Controller running Windows Server 2008 R2 through 2016 and
two Windows Enterprise computers joined to that domain.

See :doc:`environment_setup` for more information on creating a Windows Enterprise test environment

Internet Requirements
---------------------

An Internet connection is required to install CALDERA, however once installation is complete an Internet connection
is no longer required. It is possible to install CALDERA without Internet by manually copying CALDERA's dependencies to
the install server. Contact CALDERA's developers for more information.