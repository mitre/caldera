[![Release](https://img.shields.io/badge/dynamic/json?color=blue&label=Release&query=tag_name&url=https%3A%2F%2Fapi.github.com%2Frepos%2Fmitre%2Fcaldera%2Freleases%2Flatest)](https://github.com/mitre/caldera/releases/latest)
[![Testing Status](https://github.com/mitre/caldera/actions/workflows/testing.yml/badge.svg?branch=master)](https://github.com/mitre/caldera/actions/workflows/testing.yml?query=branch%3Amaster)
[![Security Status](https://github.com/mitre/caldera/actions/workflows/security.yml/badge.svg?branch=master)](https://github.com/mitre/caldera/actions/workflows/security.yml?query=branch%3Amaster)
[![codecov](https://codecov.io/gh/mitre/caldera/branch/master/graph/badge.svg)](https://codecov.io/gh/mitre/caldera)
[![Documentation Status](https://readthedocs.org/projects/caldera/badge/?version=stable)](http://caldera.readthedocs.io/?badge=stable)

# CALDERA&trade;

*Full documentation, training and use-cases can be found [here](https://caldera.readthedocs.io/en/latest/).*

CALDERA&trade; is a cyber security framework designed to easily automate adversary emulation, assist manual red-teams, and automate incident response.

It is built on the [MITRE ATT&CK™ framework](https://attack.mitre.org/) and is an active research project at MITRE.

The framework consists of two components:

1) **The core system**. This is the framework code, consisting of what is available in this repository. Included is 
an asynchronous command-and-control (C2) server with a REST API and a web interface. 
2) **Plugins**. These repositories expand the core framework capabilities and providing additional functionality. Examples include agents, reporting, collections of TTPs and more.

## Plugins

:star: Create your own plugin! Plugin generator: **[Skeleton](https://github.com/mitre/skeleton)** :star:

### Default
- **[Access](https://github.com/mitre/access)** (red team initial access tools and techniques)
- **[Atomic](https://github.com/mitre/atomic)** (Atomic Red Team project TTPs)
- **[Builder](https://github.com/mitre/builder)** (dynamically compile payloads)
- **[CalTack](https://github.com/mitre/caltack.git)** (embedded ATT&CK website)
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

## Requirements

These requirements are for the computer running the core framework:

* Any Linux or MacOS
* Python 3.6.1+ (with Pip3)
* Google Chrome is our only supported browser
* Recommended hardware to run on is 8GB+ RAM and 2+ CPUs

## Installation

Start by cloning this repository recursively, passing the desired version/release in x.x.x format. This will pull in all available plugins. If you clone master - or any non-release branch - you may experience bugs.
```Bash
git clone https://github.com/mitre/caldera.git --recursive --branch 3.0.0
```

Next, install the PIP requirements:
```Bash
pip3 install -r requirements.txt
```
**Super-power your CALDERA server installation! [Install GoLang (1.13+)](https://golang.org/doc/install)**

Finally, start the server. 
```Bash
python3 server.py --insecure
```

Collectively this would be:
```Bash
git clone https://github.com/mitre/caldera.git --recursive --branch 3.0.0
cd caldera
pip3 install -r requirements.txt
python3 server.py --insecure
```

Once started, you should log into http://localhost:8888 using the credentials red/admin. Then go into Plugins -> Training and complete the capture-the-flag style training course to learn how to use the framework.

## Video tutorial

Watch the [following video](https://www.youtube.com/watch?v=_mVGjqu03fg) for a brief run through of how to run your first operation. 

## Contributing

Refer to our [contributor documentation](CONTRIBUTING.md).

## Licensing

In addition to CALDERA&trade;'s open source capabilities, MITRE maintains several in-house CALDERA&trade; plugins that offer 
more advanced functionality. For more information, or to discuss licensing opportunities, please reach out to 
caldera@mitre.org or directly to [MITRE's Technology Transfer Office](https://www.mitre.org/about/corporate-overview/contact-us#technologycontact).
