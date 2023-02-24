[![Release](https://img.shields.io/badge/dynamic/json?color=blue&label=Release&query=tag_name&url=https%3A%2F%2Fapi.github.com%2Frepos%2Fmitre%2Fcaldera%2Freleases%2Flatest)](https://github.com/mitre/caldera/releases/latest)
[![Testing Status](https://github.com/mitre/caldera/actions/workflows/testing.yml/badge.svg?branch=master)](https://github.com/mitre/caldera/actions/workflows/testing.yml?query=branch%3Amaster)
[![Security Status](https://github.com/mitre/caldera/actions/workflows/security.yml/badge.svg?branch=master)](https://github.com/mitre/caldera/actions/workflows/security.yml?query=branch%3Amaster)
[![codecov](https://codecov.io/gh/mitre/caldera/branch/master/graph/badge.svg)](https://codecov.io/gh/mitre/caldera)
[![Documentation Status](https://readthedocs.org/projects/caldera/badge/?version=stable)](http://caldera.readthedocs.io/?badge=stable)

# CALDERA&trade;

CALDERA&trade; is a cyber security platform designed to easily automate adversary emulation, assist manual red-teams, and automate incident response.

It is built on the [MITRE ATT&CK™ framework](https://attack.mitre.org/) and is an active research project at MITRE.

The framework consists of two components:

1) **The core system**. This is the framework code, consisting of what is available in this repository. Included is
an asynchronous command-and-control (C2) server with a REST API and a web interface.
2) **Plugins**. These repositories expand the core framework capabilities and providing additional functionality. Examples include agents, reporting, collections of TTPs and more.

## Resources and Socials
* 📜 [Documentation, training, and use-cases](https://caldera.readthedocs.io/en/latest/)
* ✍️ [CALDERA's blog](https://medium.com/@mitrecaldera/welcome-to-the-official-mitre-caldera-blog-page-f34c2cdfef09)
* 🌐 [Homepage](https://caldera.mitre.org)

## Plugins

:star: Create your own plugin! Plugin generator: **[Skeleton](https://github.com/mitre/skeleton)** :star:

### Default
- **[Access](https://github.com/mitre/access)** (red team initial access tools and techniques)
- **[Atomic](https://github.com/mitre/atomic)** (Atomic Red Team project TTPs)
- **[Builder](https://github.com/mitre/builder)** (dynamically compile payloads)
- **[Compass](https://github.com/mitre/compass)** (ATT&CK visualizations)
- **[Debrief](https://github.com/mitre/debrief)** (operations insights)
- **[Emu](https://github.com/mitre/emu)** (CTID emulation plans)
- **[Fieldmanual](https://github.com/mitre/fieldmanual)** (documentation)
- **[GameBoard](https://github.com/mitre/gameboard)** (visualize joint red and blue operations)
- **[Human](https://github.com/mitre/human)** (create simulated noise on an endpoint)
- **[Manx](https://github.com/mitre/manx)** (shell functionality and reverse shell payloads)
- **[Mock](https://github.com/mitre/mock)** (simulate agents in operations)
- **[Response](https://github.com/mitre/response)** (incident response)
- **[Sandcat](https://github.com/mitre/sandcat)** (default agent)
- **[SSL](https://github.com/mitre/SSL)** (enable https for caldera)
- **[Stockpile](https://github.com/mitre/stockpile)** (technique and profile storehouse)
- **[Training](https://github.com/mitre/training)** (certification and training course)

### More
These plugins are ready to use but are not included by default:
- **[Pathfinder](https://github.com/center-for-threat-informed-defense/caldera_pathfinder)** (vulnerability scanning)
- **[SAML](https://github.com/mitre/saml)** (SAML authentication)
- **[CalTack](https://github.com/mitre/caltack.git)** (embedded ATT&CK website)

## Requirements

These requirements are for the computer running the core framework:

* Any Linux or MacOS
* Python 3.7+ (with Pip3)
* Recommended hardware to run on is 8GB+ RAM and 2+ CPUs
* Recommended: GoLang 1.17+ to dynamically compile GoLang-based agents.

## Installation

Concise installation steps:
```Bash
git clone https://github.com/mitre/caldera.git --recursive
cd caldera
pip3 install -r requirements.txt
python3 server.py --insecure
```

Full steps:
Start by cloning this repository recursively, passing the desired version/release in x.x.x format. This will pull in all available plugins.
```Bash
git clone https://github.com/mitre/caldera.git --recursive --branch x.x.x
```

Next, install the PIP requirements:
```Bash
pip3 install -r requirements.txt
```
**Super-power your CALDERA server installation! [Install GoLang (1.17+)](https://go.dev/doc/install)**

Finally, start the server.
```Bash
python3 server.py --insecure
```

Once started, log into http://localhost:8888 using the default credentials red/admin. Then go into Plugins -> Training and complete the capture-the-flag style training course to learn how to use CALDERA.

## Docker Deployment
To build a CALDERA docker image, ensure you have docker installed and perform the following actions:
```Bash
# Recursively clone the CALDERA repository if you have not done so
git clone https://github.com/mitre/caldera.git --recursive

# Build the docker image. Change image tagging as desired.
# WIN_BUILD is set to true to allow CALDERA installation to compile windows-based agents.
# Alternatively, you can use the docker compose YML file via "docker-compose build"
cd caldera
docker build . --build-arg WIN_BUILD=true -t caldera:latest

# Run the image. Change port forwarding configuration as desired.
docker run -p 8888:8888 caldera:latest
```

To gracefully terminate your docker container, do the following:
```Bash
# Find the container ID for your docker container running CALDERA
docker ps

# Send interrupt signal, e.g. "docker kill --signal=SIGINT 5b9220dd9c0f"
docker kill --signal=SIGINT [container ID]
```

## Contributing

Refer to our [contributor documentation](CONTRIBUTING.md).

## Vulnerability Disclosures

Refer to our [vulnerability discolosure documentation](SECURITY.md) for submitting bugs.

## Licensing

In addition to CALDERA&trade;'s open source capabilities, MITRE maintains several in-house CALDERA&trade; plugins that offer
more advanced functionality. For more information, or to discuss licensing opportunities, please reach out to
caldera@mitre.org or directly to [MITRE's Technology Transfer Office](https://www.mitre.org/about/corporate-overview/contact-us#technologycontact).

## Philanthropic Support

If you are interested in providing philanthropic support to sustain and evolve CALDERA&trade;'s open source capabilities, please contact us at caldera@mitre.org.
