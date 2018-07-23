FROM python:3.6
LABEL maintainer="MITRE"
ARG crater=https://github.com/mitre/caldera-crater/releases/download/v0.1.0/CraterMainWin8up.exe

COPY ./caldera /opt/caldera/caldera
WORKDIR /opt/caldera/caldera

# Install pre-requisites
RUN pip install --no-cache-dir -r requirements.txt && \
    mkdir -p ../dep/crater/crater && \
    curl $crater -k -o ../dep/crater/crater/CraterMain.exe

# Run from a non-root user
RUN groupadd -r caldera && \
useradd -m -g caldera -s /sbin/nologin -c "Caldera user" caldera && \
chown -R caldera:caldera /opt/caldera
USER caldera

# Start server
EXPOSE 8888
ENTRYPOINT ["python", "caldera.py"]
