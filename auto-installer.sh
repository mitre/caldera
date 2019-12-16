#!/bin/bash

function usage()
{
cat << EOF
usage: $0 options

This script will install all of the Caldera server requirements

OPTIONS:
	-h 	      	  Show help
	--ubuntu      Install on a debian/ubuntu system
	--centos      Install on a centos/redhat system
	--darwin      Install on a darwin/mac system

EOF
}


function install_wrapper() {
    echo "[-] Checking for $1"
    which $2
    if [[ $? != 0 ]]; then
        echo "[-] Installing $1"
        eval $3
        echo "[+] $1 installed"
    else
        echo "[+] $1 already installed"
    fi
}

function all_install_go_dependencies() {
    echo "[-] Installing on GO dependencies"
    go get "github.com/google/go-github/github"
    go get "golang.org/x/oauth2"
    echo "[+] GO dependencies installed"
}

function all_install_python_requirements() {
    pip3 install virtualenv
    virtualenv calderaenv
    source calderaenv/bin/activate
    pip install -r ./requirements.txt
}

function darwin_install_homebrew() {
    install_wrapper "Homebrew" brew "/usr/bin/ruby -e \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)\""
}

function darwin_install_go() {
    install_wrapper "GO" go "brew install go"
}

function darwin_install_mingw() {
    install_wrapper "MinGW" x86_64-w64-mingw32-gcc "brew install mingw-w64"
}

function darwin_install_python() {
    install_wrapper "Python" python3 "brew install python"
}

function ubuntu_install_go() {
    install_wrapper "GO" go "add-apt-repository -y ppa:longsleep/golang-backports && apt-get update -y && apt-get install -y golang-go"
}

function ubuntu_install_mingw() {
    install_wrapper "MinGW" x86_64-w64-mingw32-gcc "apt-get install -y mingw-w64"
}

function ubuntu_install_python() {
    install_wrapper "Python" python3 "apt-get install -y software-properties-common && add-apt-repository -y ppa:deadsnakes/ppa && apt-get update -y && apt-get install -y python3.7"
}

function centos_install_go() {
    install_wrapper "GO" go "yum install -y epel-release && yum update -y && wget https://dl.google.com/go/go1.13.linux-amd64.tar.gz && tar -C /usr/local -xzf go1.13.linux-amd64.tar.gz && export PATH=$PATH:/usr/local/go/bin && source ~/.bash_profile"
}

function centos_install_mingw() {
    install_wrapper "MinGW" x86_64-w64-mingw32-gcc "yum install -y mingw64-gcc"
}

function centos_install_python() {
    install_wrapper "Python" python3 "yum install -y gcc openssl-devel bzip2-devel libffi libffi-devel && cd /root && wget https://www.python.org/ftp/python/3.8.0/Python-3.8.0.tgz && tar xzf Python-3.8.0.tgz && cd Python-3.8.0 && ./configure --enable-optimizations && make altinstall && rm -f /root/Python-3.8.0.tgz && ln -fs /usr/bin/python3.7 /usr/bin/python3"
}

function display_welcome_msg() {
cat << EOF
[+] Caldera environment built
[+] Start the server by copy pasting these commands into the terminal

    source calderaenv/bin/activate
    python server.py

EOF
}

function darwin() {
    echo "[-] Installing on OS X..."
    darwin_install_homebrew
    darwin_install_go
    darwin_install_mingw
    darwin_install_python
    all_install_go_dependencies
    all_install_python_requirements
    display_welcome_msg
}

function ubuntu() {
    [[ $EUID -ne 0 ]] && echo "You must run the script with sudo." && exit 1
    echo "[-] Installing on Ubuntu (Debian)..."
    ubuntu_install_go
    ubuntu_install_mingw
    ubuntu_install_python
    all_install_go_dependencies
    all_install_python_requirements
    display_welcome_msg
}

function centos() {
    [[ $EUID -ne 0 ]] && echo "You must run the script with sudo." && exit 1
    echo "[-] Installing on CentOS (RedHat)..."
    centos_install_go
    centos_install_mingw
    centos_install_python
    all_install_go_dependencies
    all_install_python_requirements
    display_welcome_msg
}

if [[ "$1" != "" ]]; then
    case $1 in
        -d | --darwin )     darwin
                            ;;
        -u | --ubuntu )     ubuntu
                            ;;
        -c | --centos )     centos
                            ;;
        -h | --help )       usage
                            exit
                            ;;
        * )                 usage
                            exit 1
    esac
fi


