==================
Build Instructions
==================

The following are build instruction for the **CALDERA** agent and Crater. They should not be necessary for normal
users.

Cagent Build Instructions
=========================

#. *Install Python 3.5*
    Install Python 3.5 can be acquired from the Operating System's package manager or from https://www.python.org/ .
    The standard installation is straightforward.
#. *Upgrade to setuptools 24.0 or later*
    The python package setuptools, version 24.0 or later must be installed. Setuptools comes with Python 3.5, but some
    versions may not be up to date. To update it, run

    .. code-block:: console

        pip install --upgrade setuptools
#. *Install Visual C++ 2015 Build Tools*
    Install the `Visual C++ 2015 Build Tools <http://landinghub.visualstudio.com/visual-cpp-build-tools>`_. During
    install check Windows 8.1 SDK and Windows 10 SDK options.

    .. note::  If Visual Studio 2015 is already installed,
        `Visual C++ 2015 Build Tools <http://landinghub.visualstudio.com/visual-cpp-build-tools>`_ should not need to be
        installed
#. *Install PyWin32 v.220*
    `PyWin32 v.220 <https://sourceforge.net/projects/pywin32/files/pywin32/Build%20220/>`_ must be installed
#. *Install py2exe*
    A modified version of py2exe must be installed. It should be provided with CALDERA and installed by executing
    ``easy_install py2exe-0.9.2.2-py3.5.egg``
#. *Install additional Python Dependences*
    Additional Python dependencies are downloaded and installed automatically by running the following command within
    the `caldera/dep/caldera-agent/` directory

    .. code-block:: console

        pip install -r requirements.txt

#. *Compile Caldera Agent*
    Compile the Caldera agent by running the following command *twice* within the `caldera/dep/caldera-agent/caldera_agent/` directory:

    .. code-block:: console

        python setup.py

After running the above command *twice* the caldera agent executable will be built and located at `caldera/dep/caldera-agent/caldera_agent/dist/cagent.exe`

Crater Build Instructions
=========================

Crater must be compiled on a Windows system. If the Caldera server is installed on a Linux system, Crater must be
built on Windows and then copied to its build location: `caldera/dep/crater/crater/CraterMain.exe`

1. *Install Mono*
    `Download <http://www.mono-project.com/download/>`_ and install Mono.

2. *Run build.bat*
    Navigate to the `caldera/dep/crater/crater` and execute `build.bat`