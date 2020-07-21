FROM debian:10.4

WORKDIR /usr/src/app

RUN apt-get update && \
    apt-get -y install python3 python3-pip golang git

#WIN_BUILD is used to enable windows build in sandcat plugin
ARG WIN_BUILD=false
RUN if [ "$WIN_BUILD" = "true" ] ; then apt-get -y install mingw-w64; fi

ADD requirements.txt .

RUN pip3 install --no-cache-dir -r requirements.txt

ADD . .

EXPOSE 8888
EXPOSE 7010
EXPOSE 7011/udp
EXPOSE 7012

ENTRYPOINT ["python3", "server.py"]
