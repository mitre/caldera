ARG PYTHON_VERSION=3.13
ARG NODE_VERSION=23

#----( UI Build Stage )--------------------------------
FROM node:${NODE_VERSION}-bookworm-slim AS ui-build

# There are two variants - slim and full
# The slim variant excludes some dependencies of *emu* and *atomic* that 
# can be downloaded on-demand if needed.
ARG VARIANT=full

# Display an error if variant is set incorrectly, otherwise just print information regarding which variant is in use
RUN if [ "$VARIANT" = "full" ]; then \
        echo "Building \"full\" container suitable for offline use!"; \
    elif [ "$VARIANT" = "slim" ]; then \
        echo "Building slim container - some plugins (emu, atomic) may not be available without an internet connection!"; \
    else \
        echo "Invalid Docker build-arg for VARIANT! Please provide either \"full\" or \"slim\"."; \
        exit 1; \
fi

RUN apt-get update -qy \
 && apt-get install -y --no-install-recommends git ca-certificates \
 && rm -rf /var/lib/apt/lists/*

ENV APP_DIR=/usr/src/app
ADD . ${APP_DIR}
WORKDIR ${APP_DIR}

# Ensure plugin submodules are loaded
RUN git config --global --add safe.directory ${APP_DIR} \
 && git submodule sync --recursive \
 && git submodule update --init --recursive

# Fetch atomic data or disable it in slim
RUN if [ "$VARIANT" = "full" ] && [ ! -d "${APP_DIR}/plugins/atomic/data/atomic-red-team" ]; then \
        git clone --depth 1 https://github.com/redcanaryco/atomic-red-team.git ${APP_DIR}/plugins/atomic/data/atomic-red-team; \
    else \
        sed -i '/\- atomic/d' ${APP_DIR}/conf/default.yml; \
    fi

# Fetch emu data
# (Emu is not enabled by default, no need to disable it if slim variant is being built)
RUN if [ "$VARIANT" = "full" ] && [ ! -d "${APP_DIR}/plugins/emu/data/adversary-emulation-plans" ]; then \
        git clone --depth 1 https://github.com/center-for-threat-informed-defense/adversary_emulation_library.git ${APP_DIR}/plugins/emu/data/adversary-emulation-plans; \
    fi

# Remove .git folders
RUN (find ${APP_DIR} -type d -name ".git") | xargs rm -rf

# Build VueJS front-end
RUN cd ${APP_DIR}/plugins/magma \
 && npm install \
 && npm run build

#----( Python/Go Build Stage )----------------------
FROM python:${PYTHON_VERSION}-slim-bookworm AS build

# Install Go
ARG TARGETARCH
ARG GO_VERSION=1.25.4

RUN apt-get update -qy \
 && apt-get install -y --no-install-recommends ca-certificates curl bash build-essential python3-dev\
 && rm -rf /var/lib/apt/lists/*

RUN set -eux; \
  case "$TARGETARCH" in \
    amd64|arm64) \
      echo "Installing Go ${GO_VERSION} for $TARGETARCH"; \
      curl -fsSL "https://go.dev/dl/go${GO_VERSION}.linux-${TARGETARCH}.tar.gz" -o /tmp/go.tgz; \
      tar -C /usr/local -xzf /tmp/go.tgz; \
      rm -f /tmp/go.tgz ;; \
    *) \
      echo "Unsupported arch $TARGETARCH, ignoring Go install"; \
      mkdir -p /usr/local/go/bin ;; \
  esac

ENV APP_DIR=/usr/src/app
RUN python3 -m venv ${APP_DIR}
ENV PATH="/usr/local/go/bin:$PATH"
ENV PATH="/usr/src/app/bin:$PATH"

COPY --from=ui-build /usr/src/app /usr/src/app
WORKDIR ${APP_DIR}

# Install Python dependencies, allowing failed installs for plugin requirements
RUN pip install --upgrade pip \
 && sed -i '/^lxml.*/d' ${APP_DIR}/requirements.txt \
 && pip install -r ${APP_DIR}/requirements.txt \
 && find ${APP_DIR}/plugins/ -type f -name 'requirements.txt' -print0 | xargs -0 -n1 pip install --no-cache-dir -r || true

# Rebuild Sandcat agents if Go is installed
RUN set -eux; \
  if [ -x /usr/local/go/bin/go ]; then \
    echo "Building Sandcat agents"; \
    cd ${APP_DIR}/plugins/sandcat/gocat; \
    go mod tidy; \
    go mod download; \
    cd ${APP_DIR}/plugins/sandcat; \
    sed -i 's/\r$//' update-agents.sh; \
    chmod +x update-agents.sh; \
    ./update-agents.sh; \
  fi

#----( Runtime Stage )-------------------------------------------
FROM python:${PYTHON_VERSION}-slim-bookworm AS runtime

COPY --from=build /usr/local/go /usr/local/go
COPY --from=build /usr/src/app /app

# Set timezone (default to UTC)
ARG TZ="UTC"
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo $TZ > /etc/timezone

# Install caldera dependencies TODO: what are the actual requirements?
RUN apt-get update -qy \
 && apt-get --no-install-recommends -y install git curl ca-certificates unzip mingw-w64 zlib1g gcc \
 && rm -rf /var/lib/apt/lists/*

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

# Run as user: app
RUN groupadd -r app && \
    useradd -r -d /app -g app -N app;

USER app
WORKDIR /app
ENV PATH="/usr/local/go/bin:$PATH"
ENV PATH="/app/bin:$PATH"

CMD ["python3", "-I", "/app/server.py"]
