FROM ubuntu:focal

ARG TZ="UTC"
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo $TZ > /etc/timezone

WORKDIR /usr/src/app

RUN apt-get update && \
    apt-get -y install python3 python3-pip golang git

#WIN_BUILD is used to enable windows build in sandcat plugin
ARG WIN_BUILD=false
RUN if [ "$WIN_BUILD" = "true" ] ; then apt-get -y install mingw-w64; fi

# Install pip requirements
ADD requirements.txt .

RUN pip3 install --no-cache-dir -r requirements.txt

ADD . .

# Download golang dependencies
RUN go get github.com/grandcat/zeroconf github.com/google/go-github/github github.com/grandcat/zeroconf github.com/miekg/dns golang.org/x/oauth2 gopkg.in/natefinch/npipe.v2

# Update default sandcat agent binaries
WORKDIR /usr/src/app/plugins/sandcat

RUN ./update-agents.sh

# Check if we can compile the sandcat extensions
RUN mkdir /tmp/gocatextensionstest

RUN cp -R ./gocat-extensions /tmp/gocatextensionstest/gocat

RUN cp -R ./gocat /tmp/gocatextensionstest/
RUN cp ./update-agents.sh /tmp/gocatextensionstest/update-agents.sh

WORKDIR /tmp/gocatextensionstest

RUN mkdir /tmp/gocatextensionstest/payloads

RUN ./update-agents.sh

# Clone atomic red team repo for the atomic plugin
RUN git clone --depth 1 https://github.com/redcanaryco/atomic-red-team.git /usr/src/app/plugins/atomic/data/atomic-red-team

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
