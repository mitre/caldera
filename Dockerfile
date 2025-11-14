ARG PYTHON_VERSION=3.13
ARG GO_VERSION=1.25.4
ARG NODE_VERSION=23.9.0

#----( Build Stage )--------------------------------
FROM python:${PYTHON_VERSION}-slim-bookworm AS build

# There are two variants - slim and full
# The slim variant excludes some dependencies of *emu* and *atomic* that 
# can be downloaded on-demand if needed.
ARG VARIANT=full
RUN if [ "$VARIANT" = "full" ]; then \
        echo "Building full Caldera container - downloading emu and atomic dependencies for offline use"; \
    elif [ "$VARIANT" = "slim" ]; then \
        echo "Building slim Caldera container - emu and atomic may not be available without an internet connection"; \
    else \
        echo "Invalid Docker build-arg for VARIANT! Please provide either \"full\" or \"slim\"."; \
        exit 1; \
fi

RUN apt-get update -qy \
 && apt-get install -y --no-install-recommends git ca-certificates curl bash xz-utils build-essential \
 && rm -rf /var/lib/apt/lists/*

# Install Node
ARG TARGETARCH
ARG NODE_VERSION
RUN set -eux; \
    arch="${TARGETARCH:-amd64}"; \
    case "$arch" in \
      amd64) node_arch="x64" ;; \
      arm64) node_arch="arm64" ;; \
      *) node_arch="x64" ;; \
    esac; \
    curl -fsSL "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-${node_arch}.tar.xz" -o /tmp/node.tar.xz; \
    mkdir -p /usr/local/lib/node; \
    tar -xJf /tmp/node.tar.xz -C /usr/local/lib/node --strip-components=1; \
    rm -f /tmp/node.tar.xz

# Install Go
ARG GO_VERSION
RUN set -eux; \
  arch="${TARGETARCH:-amd64}"; \
  case "$arch" in \
    amd64|arm64) \
      go_arch="$arch"; \
      echo "Installing Go ${GO_VERSION} for ${go_arch}"; \
      curl -fsSL "https://go.dev/dl/go${GO_VERSION}.linux-${go_arch}.tar.gz" -o /tmp/go.tgz; \
      tar -C /usr/local -xzf /tmp/go.tgz; \
      rm -f /tmp/go.tgz ;; \
    *) \
      echo "Unsupported arch ${arch}, ignoring Go install"; \
      mkdir -p /usr/local/go/bin && touch /usr/local/go/bin/.install_failed ;; \
  esac

ENV APP_DIR=/usr/src/app
RUN python3 -m venv ${APP_DIR}
ENV PATH="/usr/local/go/bin:${PATH}"
ENV PATH="${APP_DIR}/bin:$PATH"

ADD . ${APP_DIR}
WORKDIR ${APP_DIR}

# Ensure plugin submodules have been cloned
RUN git config --global --add safe.directory ${APP_DIR} \
 && git submodule sync --recursive \
 && git submodule update --init --recursive

# Install Python dependencies 
# Note: Ignoring core lxml version due to failed builds 
# Note: Allowing failed installs for plugin requirements
RUN pip install --upgrade pip \
 && sed -i '/^lxml.*/d' ${APP_DIR}/requirements.txt \
 && pip install -r ${APP_DIR}/requirements.txt \
 && find ${APP_DIR}/plugins/ -type f -name 'requirements.txt' -print0 | xargs -0 -n1 pip install --no-cache-dir -r || true

# Rebuild Sandcat agents if Go is installed
RUN set -eux; \
  if command -v go >/dev/null 2>&1; then \
    echo "Building Sandcat agents"; \
    cd ${APP_DIR}/plugins/sandcat/gocat; \
    go mod tidy; \
    go mod download; \
    cd ${APP_DIR}/plugins/sandcat; \
    sed -i 's/\r$//' update-agents.sh; \
    chmod +x update-agents.sh; \
    ./update-agents.sh; \
  fi

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
RUN (find ${APP_DIR} -type d -name ".git") | xargs rm -rf \
 && rm ${APP_DIR}/.gitmodules


#----( Runtime Stage )--------------------------------
FROM python:${PYTHON_VERSION}-slim-bookworm AS runtime

ENV APP_DIR=/usr/src/app

# Create runtime user: app
RUN groupadd --system app \
 && useradd --system --home-dir ${APP_DIR} --uid 1001 --gid app -N app

COPY --from=build /usr/local/go /usr/local/go
COPY --from=build /usr/local/lib/node /usr/local/lib/node
COPY --from=build --chown=app:app /usr/src/app ${APP_DIR}

# Set timezone (default to UTC)
ARG TZ="UTC"
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo $TZ > /etc/timezone

# Install Caldera runtime dependencies
RUN apt-get update -qy \
 && apt-get --no-install-recommends -y install git curl ca-certificates unzip mingw-w64 zlib1g \
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
USER app
WORKDIR ${APP_DIR}
ENV PATH="/usr/local/go/bin:${PATH}"
ENV PATH="${APP_DIR}/bin:${PATH}"
ENV PATH="/usr/local/lib/node/bin:${PATH}"

# Build VueJS front-end
RUN cd ${APP_DIR}/plugins/magma \
 && npm install \
 && npm run build

CMD ["python3", "-I", "/usr/bin/app/server.py", "--insecure"]
