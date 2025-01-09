[![Release](https://img.shields.io/badge/dynamic/json?color=blue&label=Release&query=tag_name&url=https%3A%2F%2Fapi.github.com%2Frepos%2Fmitre%2Fcaldera%2Freleases%2Flatest)](https://github.com/mitre/caldera/releases/latest)
[![Testing Status](https://github.com/mitre/caldera/actions/workflows/quality.yml/badge.svg?branch=master)](https://github.com/mitre/caldera/actions/workflows/quality.yml?query=branch%3Amaster)
[![Security Status](https://github.com/mitre/caldera/actions/workflows/security.yml/badge.svg?branch=master)](https://github.com/mitre/caldera/actions/workflows/security.yml?query=branch%3Amaster)
[![codecov](https://codecov.io/gh/mitre/caldera/branch/master/graph/badge.svg)](https://codecov.io/gh/mitre/caldera)
[![Documentation Status](https://readthedocs.org/projects/caldera/badge/?version=stable)](http://caldera.readthedocs.io/?badge=stable)

# MITRE Caldera&trade;

MITRE Caldera&trade; is a cyber security platform designed to easily automate adversary emulation, assist manual red-teams, and automate incident response.

It is built on the [MITRE ATT&CK™ framework](https://attack.mitre.org/) and is an active research project at MITRE.

The framework consists of two components:

1) **The core system**. This is the framework code, consisting of what is available in this repository. Included is
an asynchronous command-and-control (C2) server with a REST API and a web interface.
2) **Plugins**. These repositories expand the core framework capabilities and providing additional functionality. Examples include agents, reporting, collections of TTPs and more.

## Resources & Socials
* 📜 [Documentation, training, and use-cases](https://caldera.readthedocs.io/en/latest/)
* ✍️ [Caldera's blog](https://medium.com/@mitrecaldera/welcome-to-the-official-mitre-caldera-blog-page-f34c2cdfef09)
* 🌐 [Homepage](https://caldera.mitre.org)

## Plugins

:star: Create your own plugin! Plugin generator: **[Skeleton](https://github.com/mitre/skeleton)** :star:

### Default
These plugins are supported and maintained by the Caldera team.
- **[Access](https://github.com/mitre/access)** (red team initial access tools and techniques)
- **[Atomic](https://github.com/mitre/atomic)** (Atomic Red Team project TTPs)
- **[Builder](https://github.com/mitre/builder)** (dynamically compile payloads)
- **[Caldera for OT](https://github.com/mitre/caldera-ot)** (ICS/OT capabilities for Caldera)
- **[Compass](https://github.com/mitre/compass)** (ATT&CK visualizations)
- **[Debrief](https://github.com/mitre/debrief)** (operations insights)
- **[Emu](https://github.com/mitre/emu)** (CTID emulation plans)
- **[Fieldmanual](https://github.com/mitre/fieldmanual)** (documentation)
- **[GameBoard](https://github.com/mitre/gameboard)** (visualize joint red and blue operations)
- **[Human](https://github.com/mitre/human)** (create simulated noise on an endpoint)
- **[Magma](https://github.com/mitre/magma)** (VueJS UI for Caldera v5)
- **[Manx](https://github.com/mitre/manx)** (shell functionality and reverse shell payloads)
- **[Response](https://github.com/mitre/response)** (incident response)
- **[Sandcat](https://github.com/mitre/sandcat)** (default agent)
- **[SSL](https://github.com/mitre/SSL)** (enable https for caldera)
- **[Stockpile](https://github.com/mitre/stockpile)** (technique and profile storehouse)
- **[Training](https://github.com/mitre/training)** (certification and training course)

### More
These plugins are ready to use but are not included by default and are not maintained by the Caldera team.
- **[Arsenal](https://github.com/mitre-atlas/arsenal)** (MITRE ATLAS techniques and profiles)
- **[BountyHunter](https://github.com/fkie-cad/bountyhunter)** (The Bounty Hunter)
- **[CalTack](https://github.com/mitre/caltack.git)** (embedded ATT&CK website)
- **[SAML](https://github.com/mitre/saml)** (SAML authentication)

## Requirements

These requirements are for the computer running the core framework:

* Any Linux or MacOS
* Python 3.8+ (with Pip3)
* Recommended hardware to run on is 8GB+ RAM and 2+ CPUs
* Recommended: GoLang 1.17+ to dynamically compile GoLang-based agents.
* NodeJS (v16+ recommended for v5 VueJS UI)

## Installation

Concise installation steps:
```Bash
git clone https://github.com/mitre/caldera.git --recursive
cd caldera
pip3 install -r requirements.txt
python3 server.py --insecure --build
```

Full steps:
Start by cloning this repository recursively, passing the desired version/release in x.x.x format. This will pull in all available plugins.
```Bash
git clone https://github.com/mitre/caldera.git --recursive --tag x.x.x
```

Next, install the PIP requirements:
```Bash
pip3 install -r requirements.txt
```
**Super-power your Caldera server installation! [Install GoLang (1.19+)](https://go.dev/doc/install)**

Finally, start the server.
```Bash
python3 server.py --insecure --build
```
The `--build` flag automatically installs any VueJS UI dependencies, bundles the UI into a dist directory, writes the Magma plugin's `.env` file, and is served by the Caldera server. You will only have to use the `--build` flag again if you add any plugins or make any changes to the UI.
Once started, log into http://localhost:8888 using the default credentials red/admin. Then go into Plugins -> Training and complete the capture-the-flag style training course to learn how to use Caldera.

In some situations the default configuration values can cause the UI to appear unresponsive due to misrouted requests. Modify the `app.frontend.api_base_url` config value and start the server using the --build flag to update the UI's request URL environment variable.

If you prefer to not use the new VueJS UI, revert to Caldera v4.2.0. Correspondingly, do not use the `--build` flag for earlier versions as not required.

### User Interface Development

If you'll be developing the UI, there are a few more additional installation steps.

**Requirements**  
* NodeJS (v16+ recommended)

**Setup**

1. Add the Magma submodule if you haven't already: `git submodule add https://github.com/mitre/magma`
1. Install NodeJS dependencies: `cd plugins/magma && npm install && cd ..`
1. Start the Caldera server with an additional flag: `python3 server.py --uidev localhost`

Your Caldera server is available at http://localhost:8888 as usual, but there will now be a hot-reloading development server for the VueJS front-end available at http://localhost:3000. Both logs from the server and the front-end will display in the terminal you launched the server from.

## Docker Deployment
To build a Caldera docker image, ensure you have docker installed and perform the following actions:
```Bash
# Recursively clone the Caldera repository if you have not done so
git clone https://github.com/mitre/caldera.git --recursive

# Build the docker image. Change image tagging as desired.
# WIN_BUILD is set to true to allow Caldera installation to compile windows-based agents.
# Alternatively, you can use the docker compose YML file via "docker-compose build"
cd caldera
docker build . --build-arg WIN_BUILD=true -t caldera:latest

# Run the image. Change port forwarding configuration as desired.
docker run -p 8888:8888 caldera:latest
```

To gracefully terminate your docker container, do the following:
```Bash
# Find the container ID for your docker container running Caldera
docker ps

# Stop the container
docker stop [container ID]
```

## Contributing

Refer to our [contributor documentation](CONTRIBUTING.md).

## Vulnerability Disclosures

Refer to our [Vulnerability Disclosure Documentation](SECURITY.md) for submitting bugs.

## Licensing

To discuss licensing opportunities, please reach out to caldera@mitre.org or directly to [MITRE's Technology Transfer Office](https://www.mitre.org/about/corporate-overview/contact-us#technologycontact).

## Caldera Benefactor Program

If you are interested in partnering to support, sustain, and evolve MITRE Caldera&trade;'s open source capabilities, please contact us at caldera@mitre.org.
