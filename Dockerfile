FROM ubuntu:latest
SHELL ["/bin/bash", "-c"]

ARG TZ="UTC"
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo $TZ > /etc/timezone

WORKDIR /usr/src/app

# Make sure user cloned caldera recursively before installing anything.
ADD . .
RUN if [ -z "$(ls plugins/stockpile)" ]; then echo "stockpile plugin not downloaded - please ensure you recursively cloned the caldera git repository and try again."; exit 1; fi

RUN apt-get update && \
    apt-get -y install python3 python3-pip git curl

#WIN_BUILD is used to enable windows build in sandcat plugin
ARG WIN_BUILD=false
RUN if [ "$WIN_BUILD" = "true" ] ; then apt-get -y install mingw-w64; fi

# Install pip requirements
RUN pip3 install --no-cache-dir -r requirements.txt

# Set up config file and disable atomic by default
RUN grep -v "\- atomic" conf/default.yml > conf/local.yml

# Install golang
RUN curl -L https://go.dev/dl/go1.17.6.linux-amd64.tar.gz -o go1.17.6.linux-amd64.tar.gz
RUN rm -rf /usr/local/go && tar -C /usr/local -xzf go1.17.6.linux-amd64.tar.gz;
ENV PATH="${PATH}:/usr/local/go/bin"
RUN go version;

# Compile default sandcat agent binaries, which will download basic golang dependencies.
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

WORKDIR /usr/src/app

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
