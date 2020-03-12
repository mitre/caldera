#!/bin/bash

SCRIPT=$(readlink -f "$0")
CALDERA_DIR=$(dirname "$SCRIPT")
USER=$(printf '%s\n' "${SUDO_USER:-$USER}")
CRITICAL=1
WARNING=0
CRITICAL_FAIL=0
WARNING_FAIL=0

function installed() {
    echo "[+] $1 installed"
    echo "[+] $1 installed">>install_log.txt
}

function failed() {
    echo "[x] "$1" FAILED to install"
    echo "[x] "$1" FAILED to install">>install_log.txt
    echo " - command: $2">>install_log.txt
}

function install_wrapper() {
    echo "[-] Checking for $1"
    which $2
    if [[ $? != 0 ]]; then
        echo "[-] Installing $1"
        if eval $3; then
            installed "$1"
        else
            failed "$1" "$3"
            if [[ $4 == 1 ]]; then
                CRITICAL_FAIL=1
            else
                WARNING_FAIL=1
            fi
        fi
    else
        echo "[+] "$1" already installed"
        echo "[+] "$1" already installed">>install_log.txt
    fi
}

function initialize_log() {
    echo "CALDERA install log">install_log.txt
}

function extra_error() {
    if [[ $? == 0 ]]; then
        installed "$2"
    else
        failed "$2" "$1"
        if [[ $3 == 1 ]]; then
        CRITICAL_FAIL=1
            echo $CRITICAL_FAIL
        else
            WARNING_FAIL=1
        fi
    fi
}

function run_uprivileged() {
  su - "$USER" -c "$1"
  extra_error "$1" "$2" "$3"
}

function all_install_go_dependencies() {
    echo "[-] Installing on GO dependencies"
    go get "github.com/google/go-github/github"
    extra_error "go get github.com/google/go-github/github" "GO github" $WARNING
    go get "golang.org/x/oauth2"
    extra_error "go get golang.org/x/oauth2" "GO oath2" $WARNING
}

function all_install_python_requirements() {
    echo "[-] Setting up Python venv"
    run_uprivileged "pip3 -q install virtualenv" "Python virtualenv" $CRITICAL
    run_uprivileged "virtualenv -q -p python3 $CALDERA_DIR/calderaenv" "Caldera python venv" $CRITICAL
    run_uprivileged "$CALDERA_DIR/calderaenv/bin/pip -q install -r $CALDERA_DIR/requirements.txt" "Caldera python requirements" $CRITICAL
}

function all_build_documentation() {
  echo "[-] Building documentation"
  run_uprivileged "$CALDERA_DIR/calderaenv/bin/sphinx-build -b html $CALDERA_DIR/docs $CALDERA_DIR/docs/_build" "sphinx documentation" $WARNING
}

function darwin_install_homebrew() {
    install_wrapper "Homebrew" brew "/usr/bin/ruby -e \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)\"" $CRITICAL
}

function darwin_install_go() {
    install_wrapper "GO" go "brew install go" $WARNING
}

function darwin_install_mingw() {
    install_wrapper "MinGW" x86_64-w64-mingw32-gcc "brew install mingw-w64" $WARNING
}

function darwin_install_python() {
    install_wrapper "Python" python3 "brew install python" $CRITICAL
}

function ubuntu_install_go() {
    install_wrapper "GO" go "apt-get install -y software-properties-common && add-apt-repository -y ppa:longsleep/golang-backports && apt-get update -y && apt-get install -y golang-go" $WARNING
}

function ubuntu_install_mingw() {
    install_wrapper "MinGW" x86_64-w64-mingw32-gcc "apt-get install -y mingw-w64" $WARNING
}

function ubuntu_install_python() {
    install_wrapper "Python" python3 "apt-get install -y software-properties-common && add-apt-repository -y ppa:deadsnakes/ppa && apt-get update -y && apt-get install -y python3.7" $CRITICAL
}

function centos_install_core_tools() {
    install_wrapper "Core" wget "yum update -y && yum install -y epel-release && yum install -y wget" $CRITICAL
}

function centos_install_go() {
    install_wrapper "GO" go "yum update -y && wget --no-check-certificate https://dl.google.com/go/go1.13.linux-amd64.tar.gz && tar -C /usr/local -xzf go1.13.linux-amd64.tar.gz && export PATH=$PATH:/usr/local/go/bin && ln -fs /usr/local/go/bin/go /usr/bin/go && source ~/.bash_profile" $WARNING
}

function centos_install_mingw() {
    install_wrapper "MinGW" x86_64-w64-mingw32-gcc "yum install -y mingw64-gcc" $WARNING
}

function centos_install_python() {
    install_wrapper "Python" python3 "yum install -y gcc openssl-devel bzip2-devel libffi libffi-devel && cd /root && wget --no-check-certificate https://www.python.org/ftp/python/3.8.0/Python-3.8.0.tgz && tar xzf Python-3.8.0.tgz && cd Python-3.8.0 && ./configure --enable-optimizations && make altinstall && rm -f /root/Python-3.8.0.tgz && ln -fs /usr/local/bin/python3.8 /usr/bin/python3 && ln -fs /usr/local/bin/pip3.8 /usr/bin/pip3 && ln -fs /usr/local/bin/virtualenv /usr/bin/virtualenv" $CRITICAL
}

function bash_set_random_conf_data() {
    echo "[-] Generating Random Values"
    sed -i.backup "s/ADMIN123/$(cat /proc/sys/kernel/random/uuid)/g" conf/default.yml
    extra_error "sed -i.backup \"s/ADMIN123/$(cat /proc/sys/kernel/random/uuid)/g\" conf/default.yml" "caldera random api_key" $WARNING
    sed -i.backup "s/REPLACE_WITH_RANDOM_VALUE/$(cat /proc/sys/kernel/random/uuid)/g" conf/default.yml
    extra_error "sed -i.backup \"s/REPLACE_WITH_RANDOM_VALUE/$(cat /proc/sys/kernel/random/uuid)/g\" conf/default.yml" "caldera random cryps_salt" $WARNING
    echo "[+] Random Values added to default.yml"
}

function display_welcome_msg() {
if [[ $CRITICAL_FAIL == 1 ]]; then
    echo "[x] Caldera installer FAILED to install critical components"
    echo "[x] See install_log.txt for details"
elif [[ $WARNING_FAIL == 1 ]]; then
    echo "[x] Caldera installer FAILED to install optional components"
    echo "[x] Caldera may run with degraded functionality"
    echo "[x] See install_log.txt for details"
    echo "[+] Caldera environment built"
    echo "[+] Start the server by copy pasting these commands into the terminal\n\n"
    echo "    source calderaenv/bin/activate"
    echo "    python server.py\n"
else
    echo "[+] Caldera environment built"
    echo "[+] Start the server by copy pasting these commands into the terminal\n\n"
    echo "    source calderaenv/bin/activate"
    echo "    python server.py\n"
fi
}

function darwin() {
    [[ $EUID -ne 0 ]] && echo "You must run the script with sudo." && exit 1
    echo "[-] Installing on OS X..."
    initialize_log
    darwin_install_homebrew
    darwin_install_go
    darwin_install_mingw
    darwin_install_python
    bash_set_random_conf_data
    all_install_go_dependencies
    all_install_python_requirements
    all_build_documentation
    display_welcome_msg
}

function ubuntu() {
    [[ $EUID -ne 0 ]] && echo "You must run the script with sudo." && exit 1
    echo "[-] Installing on Ubuntu (Debian)..."
    initialize_log
    ubuntu_install_go
    ubuntu_install_mingw
    ubuntu_install_python
    bash_set_random_conf_data
    all_install_go_dependencies
    all_install_python_requirements
    all_build_documentation
    display_welcome_msg
}

function centos() {
    [[ $EUID -ne 0 ]] && echo "You must run the script with sudo." && exit 1
    echo "[-] Installing on CentOS (RedHat)..."
    initialize_log
    centos_install_go
    centos_install_mingw
    centos_install_python
    bash_set_random_conf_data
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
else
    echo "OS not supported. Supported OS are Ubuntu, Centos, Fedora and Kali." && exit 1
fi
