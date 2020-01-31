#!/bin/bash

SCRIPT=$(readlink -f "$0")
CALDERA_DIR=$(dirname "$SCRIPT")
USER=$(printf '%s\n' "${SUDO_USER:-$USER}")

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

function run_uprivileged() {
  su - "$USER" -c "$1"
}

function all_install_go_dependencies() {
    echo "[-] Installing on GO dependencies"
    go get "github.com/google/go-github/github"
    go get "golang.org/x/oauth2"
    echo "[+] GO dependencies installed"
}

function all_install_python_requirements() {
    run_uprivileged "pip3 install virtualenv"
    run_uprivileged "virtualenv -p python3 $CALDERA_DIR/calderaenv"
    run_uprivileged "$CALDERA_DIR/calderaenv/bin/pip install -r $CALDERA_DIR/requirements.txt"
}

function all_build_documentation() {
  echo "[-] Building documentation"
  run_uprivileged "$CALDERA_DIR/calderaenv/bin/sphinx-build -b html $CALDERA_DIR/docs $CALDERA_DIR/docs/_build"
  echo "[+] Finished building documentation."
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

function centos_install_core_tools() {
    install_wrapper "Core" wget "yum update -y && yum install -y epel-release && yum install -y wget"
}

function centos_install_go() {
    install_wrapper "GO" go "yum update -y && wget --no-check-certificate https://dl.google.com/go/go1.13.linux-amd64.tar.gz && tar -C /usr/local -xzf go1.13.linux-amd64.tar.gz && export PATH=$PATH:/usr/local/go/bin && ln -fs /usr/local/go/bin/go /usr/bin/go && source ~/.bash_profile"
}

function centos_install_mingw() {
    install_wrapper "MinGW" x86_64-w64-mingw32-gcc "yum install -y mingw64-gcc"
}

function centos_install_python() {
    install_wrapper "Python" python3 "yum install -y gcc openssl-devel bzip2-devel libffi libffi-devel && cd /root && wget --no-check-certificate https://www.python.org/ftp/python/3.8.0/Python-3.8.0.tgz && tar xzf Python-3.8.0.tgz && cd Python-3.8.0 && ./configure --enable-optimizations && make altinstall && rm -f /root/Python-3.8.0.tgz && ln -fs /usr/local/bin/python3.8 /usr/bin/python3 && ln -fs /usr/local/bin/pip3.8 /usr/bin/pip3 && ln -fs /usr/local/bin/virtualenv /usr/bin/virtualenv"
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
    all_build_documentation
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
    all_build_documentation
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
    all_build_documentation
    display_welcome_msg
}

if [[ "$(uname)" == *"Darwin"* ]]; then
  darwin
elif [[ "$(lsb_release -d)" == *"Ubuntu"* ]]; then
  ubuntu
elif [[ "$(lsb_release -d)" == *"CentOS"* ]]; then
  centos
elif [[ "$(lsb_release -d)" == *"Fedora"* ]]; then
  centos
elif [[ "$(lsb_release -d)" == *"Kali"* ]]; then
  ubuntu
fi
