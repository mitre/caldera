============
Installation
============

This contains the installation instructions for **CALDERA**. **CALDERA** consists of three separate pieces of software:

CALDERA server
    The server controls the execution of CALDERA and contains a web interface for administration
CALDERA agent
    A Windows service that communicates to the CALDERA server, the CALDERA Agent is installed on every
    computer partaking in adversary emulation activities.
Crater
    A Windows executable that is used as an implant for Adversary Emulation exercises

These instructions have two sections: the first section dictates how to install the CALDERA Server along with Crater.
The second section details how to install the CALDERA Agent on each system taking part in the red team.

CALDERA Server Installation
===========================

The CALDERA server is installed on a single central server. It should be accessible over the network to all computers
that are taking part in the emulated adversary operation. Both Windows and Linux are supported however installation on
Windows requires extra installation steps. 

Several options exist for installing the server.

Option 1: Install with Docker Compose
-------------------------------------

The easiest way to install CALDERA is with Docker Compose. After installing Docker and Docker Compose. From the top-level directory simply run the following:

    .. code-block:: console

        docker-compose up

This will start the Caldera server and an instance of MongoDB. Follow the last instructions above to login to the Caldera server and change the Administrator password.

For advanced options, customize the `docker-compose.yml` file. If you are behind a proxy, uncomment three lines in the `build` section and edit the lines to include the correct information for your proxy. If you need to specify a different version of Crater (for example, if you need the Windows 7 version), you can specify it with another item under `args`: `"crater=https://github.com/mitre/caldera-crater/releases/download/v0.1.0/CraterMain7.exe"`. Other configuration options can be set in the `command` section under `server`.

Option 2: Building the Docker Container By Itself
-------------------------------------------------

Alternatively, if you want to connect to an already existing MongoDB instance, you can build the server container by itself:

    .. code-block:: console

        docker build . -t caldera

If you are behind a proxy, provide proxy information to the build process:

    .. code-block:: console

        docker build . -t caldera --build-arg http_proxy=http://proxy.example:80 --build-arg https_proxy=http://proxy.example:80

If you need to specify a different version of Crater (for example, if you need the Windows 7 version), you can specify it with another `--build-arg`:

    .. code-block:: console

        docker build . -t caldera --build-arg http_proxy=http://proxy.example:80 --build-arg https_proxy=http://proxy.example:80 --build-arg crater=https://github.com/mitre/caldera-crater/releases/download/v0.1.0/CraterMain7.exe

Then follow the instructions above regarding MongoDB.

Next run the container:

    .. code-block:: console

        docker run --net=host caldera

If you need to change any configuration parameters, for example to use a different port for MongoDB, you can do the following:

    .. code-block:: console

        docker run --net=host caldera --database.port 27020

Finally, follow the last instructions above to login to the Caldera server and change the Administrator password.

Option 3: Installing Without Docker
-----------------------------------

If you would like to install without docker, please follow the below instructions.

#. *Install Python 3.5.4 or later*
    Python 3.5.4 or later can be acquired from the Operating System's package manager or from https://www.python.org/ .
    The standard installation is straightforward.
    
    .. note:: On Linux, the development package for Python is needed. For example (may vary based on distribution and version): 
    
        .. code-block:: console
        
            apt-get install python3-dev

#. *Upgrade to setuptools 24.0 or later*
    The python package, setuptools, version 24.0 or later must be installed. Setuptools comes with Python 3.5, but some
    versions may not be up to date. To update it, run

    .. code-block:: console

        pip install --upgrade setuptools
#. *[Windows Only] Install Visual C++ 2015 Build Tools*
    Install the `Visual C++ 2015 Build Tools <http://landinghub.visualstudio.com/visual-cpp-build-tools>`_. During
    install check Windows 8.1 SDK and Windows 10 SDK options.

    .. note::  If Visual Studio 2015 is already installed,
        `Visual C++ 2015 Build Tools <http://landinghub.visualstudio.com/visual-cpp-build-tools>`_ should not need to be
        installed

#. *Install Python libraries*
    Within a command prompt navigate to the `caldera/caldera` folder and run the command

    .. code-block:: console

        pip install -r requirements.txt

    This will download and install the Python libraries necessary to run the CALDERA server.

    .. note::  When sitting behind a proxy, specific steps must be taken for pip to understand proxies. See
        `Setting your pip configuration file <https://pip.pypa.io/en/stable/user_guide/#config-file>`_. An example
        configuration file might look like the following:

        .. code-block:: console

            [global]
                proxy = http://my.proxy.name
                cert = C:\My\Path\To\SSL Certificates\chain.pem

#. *Install MongoDB*
    MongoDB 3.0 and later are supported. Most Linux distributions have MongoDB in their package manager. Otherwise
    both Windows and Linux installers can be downloaded from https://www.mongodb.com/download-center#community

#. *MongoDB Configuration*
    MongoDB must be configured to use a *replication set*. There are two ways to do this, either by modifying MongoDB's
    configuration file or by adding an additional command line flag when starting the MongoDB daemon.
    On Linux it is typically easier to edit the configuration file (typically located in `/etc/mongodb.conf`). On
    Windows it is typically easier to add an additional command line flag. Both methods are detailed below.

    **Method 1: Edit Configuration File (Recommended for Linux)**

    Depending on the version of MongoDB that you have installed, the configuration file uses two different formats.
    Old style formatting typically contains equal signs. If you see no equal signs you probably have a new style
    configuration file (See https://docs.mongodb.com/v3.2/administration/configuration/ for more information.)

    After determining what style configuration file you have, make the following modifications to it:

    Newer version of mongodb use `YAML <https://en.wikipedia.org/wiki/YAML>`_ style formatting so the following lines
    should be added (indentation intended)

    .. code-block:: console

        replication:
           replSetName: caldera

    Older versions on mongodb use key value pairs. For this style the following line should be added

    .. code-block:: console

        replSet = caldera

    **Method 2: Command Line Flag (Recommended for Windows)**

    Alternatively, the replication set parameter can also be passed in through the command line if running mongodb from
    the command line by adding the flag ``--replSet caldera`` to the command to start mongod. This is
    the easiest way to configure replication sets for Windows installs.

#. *Start MongoDB*
    MongoDB must be started. If MongoDB was installed using the Operating System's package manager, look for
    instructions on how to start the MongoDB service (typically ``service mongod start``). On Windows, MongoDB is installed
    by default in `C:\\Program Files\\MongoDB\\Server\\<version>\\bin`. Navigate to this folder on a commandline and
    run ``mongod.exe --bind_ip 127.0.0.1 --replSet caldera``

#. *[Optional] Install git*
    Git can be installed for version tracking information. It is available from Linux distributions package maintainers
    or from `git <https://git-scm.com/downloads>`_

#. *Install CraterMain.exe*
    The `CraterMain.exe` binary needs to be accessible to CALDERA. It should be placed
    in: `caldera/dep/crater/crater/CraterMain.exe` on the computer that the CALDERA server is installed on.
    Pre-built copies of CraterMain.exe are available `here <https://github.com/mitre/caldera-crater/releases>`_.

#. *Start the CALDERA server*
    The Caldera server can now be started by navigating to the `caldera/caldera` directory and running
    ``python caldera.py``.
    The first time CALDERA is run, it will generate an OpenSSL command line which can be run to create an SSL keypair
    for encrypted communication. If CALDERA is installed on a Linux machine, OpenSSL is typically already installed and
    available. On Windows computers, OpenSSL can be installed or, this command should be executed on a Linux computer
    (with the appropriate hostname substituted).

#. *Login to the Caldera server*
    The CALDERA server exposes a web service available on `<https://localhost:8888>`_. Navigate to this URL to access
    CALDERA's administration panel. The default username and password

    .. code-block:: console

        username: admin
        password: caldera

#. *Change the Administrator Password*
    Click on the top right button labeled "admin (Admin)" and select "Change Password" to change the default password
    to something unique and secret.

CALDERA is now installed. Proceed to the next section to install CALDERA Agents.

CALDERA Agent Installation
==========================

The CALDERA Agent or cagent, is installed on every computer participating in the Adversary Emulation. It should be
accessible over the network to the CALDERA server. Once configured, each cagent will register with the CALDERA server
making its computer available as an option in an operation. Pre-built cagent binaries are available 
`here <https://github.com/mitre/caldera-agent/releases>`_.

Operating System Support
------------------------

*Windows 7, 8, 8.1 or 10, 64 bit*
    A 64 bit version of Windows 7, 8, 8.1 or 10 is required.

Installation Instructions
-------------------------

#. If not already done, install the CALDERA server

#. Install the `Visual C++ Redistributable for Visual Studio 2015 <https://www.microsoft.com/en-us/download/details.aspx?id=48145>`_

   .. note:: The Visual C++ Redistributable may fail to install if Windows is not fully updated. If you encounter
       problems try fully updating Windows.

#. Download the `latest release of cagent <https://github.com/mitre/caldera-agent/releases>`_. Place cagent.exe in the desired installation location (the recommended location is `C:\\Program Files\\cagent\\cagent.exe`)

#. In the same directory, place the `conf.yml` file which can be downloaded from the CALDERA server by navigating to ::

    https://my-caldera-server:8888/conf.yml

   .. note:: The conf.yml is unique to the CALDERA server. When migrating agents to a new server, you will have to
        update the conf.yml file

   .. warning:: To prevent unauthorized users from modifying cagent.exe or conf.yml ensure the directory
        that contains these files is only editable by Administrators

#. In an Administrator command prompt install cagent with: ::

    cagent.exe --startup auto install


#. In an Administrator command prompt start cagent with: ::

    cagent.exe start

Agents that are connected to the CALDERA server are visible by checking the `Debug>Connected Agents` tab.
