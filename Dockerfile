FROM ubuntu:24.04
SHELL ["/bin/bash", "-c"]

ARG TZ="UTC"
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo $TZ > /etc/timezone

WORKDIR /usr/src/app

# Make sure user cloned caldera recursively before installing anything.
ADD . .
RUN if [ -z "$(ls plugins/stockpile)" ]; then echo "stockpile plugin not downloaded - please ensure you recursively cloned the caldera git repository and try again."; exit 1; fi

RUN apt-get update && \
    apt-get -y install python3 python3-pip python3-venv git curl golang-go


#WIN_BUILD is used to enable windows build in sandcat plugin
ARG WIN_BUILD=false
RUN if [ "$WIN_BUILD" = "true" ] ; then apt-get -y install mingw-w64; fi

# Set up python virtualenv
ENV VIRTUAL_ENV=/opt/venv/caldera
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install pip requirements
RUN pip3 install --no-cache-dir -r requirements.txt

# Set up config file and disable atomic by default
RUN python3 -c "import app; import app.utility.config_generator; app.utility.config_generator.ensure_local_config();"; \
    sed -i '/\- atomic/d' conf/local.yml;

# Compile default sandcat agent binaries, which will download basic golang dependencies.

# Install Go dependencies
WORKDIR /usr/src/app/plugins/sandcat/gocat
RUN go mod tidy && go mod download

WORKDIR /usr/src/app/plugins/sandcat

# Fix line ending error that can be caused by cloning the project in a Windows environment
RUN if [ "$WIN_BUILD" = "true" ] ; then cp ./update-agents.sh ./update-agents-copy.sh; fi
RUN if [ "$WIN_BUILD" = "true" ] ; then tr -d '\15\32' < ./update-agents-copy.sh > ./update-agents.sh; fi
RUN if [ "$WIN_BUILD" = "true" ] ; then rm ./update-agents-copy.sh; fi

RUN ./update-agents.sh

# Check if we can compile the sandcat extensions, which will download golang dependencies for agent extensions
RUN mkdir /tmp/gocatextensionstest

RUN cp -R ./gocat /tmp/gocatextensionstest/gocat
RUN cp -R ./gocat-extensions/* /tmp/gocatextensionstest/gocat/

RUN cp ./update-agents.sh /tmp/gocatextensionstest/update-agents.sh

WORKDIR /tmp/gocatextensionstest

RUN mkdir /tmp/gocatextensionstest/payloads

RUN ./update-agents.sh

# Clone atomic red team repo for the atomic plugin
RUN if [ ! -d "/usr/src/app/plugins/atomic/data/atomic-red-team" ]; then   \
    git clone --depth 1 https://github.com/redcanaryco/atomic-red-team.git \
        /usr/src/app/plugins/atomic/data/atomic-red-team;                  \
fi

WORKDIR /usr/src/app/plugins/emu

# If emu is enabled, complete necessary installation steps
RUN if [ $(grep -c "\- emu" ../../conf/local.yml)  ]; then \
    apt-get -y install zlib1g unzip;                \
    pip3 install -r requirements.txt;               \
    ./download_payloads.sh;                         \
fi

WORKDIR /usr/src/app

# Install Node.js, npm, and other build VueJS front-end
RUN apt-get update && \
    apt-get install -y nodejs npm && \
    # Directly use npm to install dependencies and build the application
    (cd plugins/magma && npm install) && \
    (cd plugins/magma && npm run build) && \
    # Remove Node.js, npm, and other unnecessary packages
    apt-get remove -y nodejs npm && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

WORKDIR /usr/src/app

STOPSIGNAL SIGINT

# Default HTTP port for web interface and agent beacons over HTTP
EXPOSE 8888

# Default HTTPS port for web interface and agent beacons over HTTPS (requires SSL plugin to be enabled)
EXPOSE 8443

# TCP and UDP contact ports
EXPOSE 7010
EXPOSE 7011/udp

# Websocket contact port
EXPOSE 7012

# Default port to listen for DNS requests for DNS tunneling C2 channel
EXPOSE 8853

# Default port to listen for SSH tunneling requests
EXPOSE 8022

# Default FTP port for FTP C2 channel
EXPOSE 2222

ENTRYPOINT ["python3", "server.py"]
