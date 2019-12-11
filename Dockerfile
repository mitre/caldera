FROM ubuntu:bionic
WORKDIR /usr/src/app
ADD . /usr/src/app
ENV GOPATH=/usr/bin/go
RUN apt-get update && \
    apt-get install python3 python3-pip golang -y && \
    pip3 install --no-cache-dir -r requirements.txt
ENTRYPOINT ["python3", "server.py"]
