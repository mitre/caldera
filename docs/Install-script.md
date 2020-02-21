Install script
==============

If you would like to install CALDERA quickly using our recommended approach, you should use the install.sh script, found at the root of the project. This script can be run on MacOS, Ubuntu and CentOS computers:
```
./install.sh --darwin
./install.sh --centos
./install.sh --ubuntu
./install.sh --kali
```

This installer will additionally install:

## A Python virtual environment

A new virtualenv for Python will be created at the root of the project, called calderaenv. All PIP requirements will be installed here instead of the host machine directly.

## GoLang

This is used to dynamically compile the 54ndc47 agent every time it is requested, giving it a new file hash each time. If GoLang is not installed on the server, the agent will be downloaded from the sandcat/payloads directory and will not be dynamically compiled.
> If GoLang is installed, you can dynamically compile any Go payload per request by simply utilizing the file_svc:compile_go function. You'll see examples of this in the sandcat and terminal plugins.

## MinGW

MinGW enables gcc compiling support for windows platforms. CALDERA uses MinGW to build C-Shared library (DLLs) versions of Sandcat.
