FROM debian:latest

RUN set -ex; \
  apt-get update; \
  apt-get install -y git mongodb python3-dev python3-pip wget openssl; \
  pip3 install --upgrade setuptools; \
  rm /etc/mongodb.conf; \
  mkdir -p /root/caldera;
COPY docker/conf/mongodb.conf  /etc
COPY build.py /root/caldera/build.py
COPY caldera/ /root/caldera/caldera/
COPY docs/ /root/caldera/docs/
COPY scripts/ /root/caldera/scripts/

RUN cd /root/caldera/caldera; \
    pip3 install -r requirements.txt; \
    cd ../; \
    mkdir -p dep/crater/crater; \
    cd /root/caldera/dep/crater/crater; \
    wget -O CraterMain.exe "https://github.com/mitre/caldera-crater/releases/download/v0.1.0/CraterMainWin8up.exe"; \
    cd /root/caldera/caldera/www/static/css; \
    wget -O vcpp_compiler.exe "https://www.microsoft.com/en-us/download/confirmation.aspx?id=48145"; \
    wget -O cagent.exe "https://github.com/mitre/caldera-agent/releases/download/v0.1.0/cagent.exe";\
    apt-get remove -y --purge wget; \
    mkdir -p /conf;
EXPOSE 8888
ENTRYPOINT service mongodb start && cd /root/caldera/caldera && python3 caldera.py && /bin/bash
