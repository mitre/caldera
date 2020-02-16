[![Release](https://img.shields.io/badge/dynamic/json?color=blue&label=Release&query=tag_name&url=https%3A%2F%2Fapi.github.com%2Frepos%2Fmitre%2Fcaldera%2Freleases%2Flatest)](https://github.com/mitre/caldera/releases/latest)
[![Build Status](https://travis-ci.com/mitre/caldera.svg?branch=master)](https://travis-ci.com/mitre/caldera)
[![Documentation Status](https://readthedocs.org/projects/caldera/badge/?version=stable)](http://caldera.readthedocs.io/?badge=stable)

**[Sandcat](https://github.com/mitre/sandcat)**|**[Mock](https://github.com/mitre/mock)**|**[Terminal](https://github.com/mitre/terminal)**|**[SSL](https://github.com/mitre/SSL)**|**[Stockpile](https://github.com/mitre/stockpile)**|**[Caltack](https://github.com/mitre/caltack)**|**[Compass](https://github.com/mitre/compass)**|**[Access](https://github.com/mitre/access)**
:-----:|:-----:|:-----:|:-----:|:-----:|:-----:|:-----:|:-----:
[![Build Status](https://travis-ci.com/mitre/sandcat.svg?branch=master)](https://travis-ci.com/mitre/sandcat)|[![Build Status](https://travis-ci.com/mitre/mock.svg?branch=master)](https://travis-ci.com/mitre/mock)|[![Build Status](https://travis-ci.com/mitre/terminal.svg?branch=master)](https://travis-ci.com/mitre/terminal)|[![Build Status](https://travis-ci.com/mitre/ssl.svg?branch=master)](https://travis-ci.com/mitre/ssl)|[![Build Status](https://travis-ci.com/mitre/stockpile.svg?branch=master)](https://travis-ci.com/mitre/stockpile)|[![Build Status](https://travis-ci.com/mitre/caltack.svg?branch=master)](https://travis-ci.com/mitre/caltack)|[![Build Status](https://travis-ci.com/mitre/compass.svg?branch=master)](https://travis-ci.com/mitre/compass)|[![Build Status](https://travis-ci.com/mitre/access.svg?branch=master)](https://travis-ci.com/mitre/access)

# CALDERA
### Cyber Adversary Language and Decision Engine for Red Team Automation

CALDERA is a cyber security framework designed to easily run autonomous breach-and-simulation exercises. It can also be used to run manual red-team engagements or automated incident response.

It is built on the [MITRE ATT&CK™ framework](https://attack.mitre.org/) and is an active research project at MITRE.

The framework consists of two components:

1) **The core system**. This is the framework code, consisting of what is available in this repository. Included is 
an asynchronous command-and-control (C2) server with a REST API and a web interface. 
2) **Plugins**. These are separate repositories that hang off of the core framework, providing additional functionality. 
Examples include agents, GUI interfaces, collections of TTPs and more. 

## Requirements

These requirements are for the computer running the core framework:

* Any Linux or MacOS
* Python 3.6.1+
* Google Chrome or Safari are our only supported browsers
* Recommended hardware to run on is 8GB+ RAM and 2+ CPUs

## Installation

Start by cloning this repository recursively, passing the desired version/release in x.x.x format. 
This will pull all available [plugins](https://caldera.readthedocs.io/en/latest/What-is-a-plugin.html).
```
git clone https://github.com/mitre/caldera.git --recursive --branch x.x.x 
```

Next install the PIP requirements
```
pip install -r requirements.txt
```
> Instead of running the step above, you could run the [auto-installer.sh](https://caldera.readthedocs.io/en/latest/Auto-install-script.html) 
script to automatically configure CALDERA in our recommended way. 

Finally, start the server
```
python server.py
```

## Video tutorial

Watch the following video for a brief run through of how to run your first operation. Alternatively, check out our [documentation](https://caldera.readthedocs.io/en/latest/) to read about the various ways to utilize this framework for offensive and defensive use-cases. 

[![IMAGE ALT TEXT HERE](https://img.youtube.com/vi/GukTj-i3UDg/0.jpg)](https://www.youtube.com/watch?v=GukTj-i3UDg)

## Developers

Want to contribute to this project? We use the basic feature branch GIT flow. Fork this repository and create a feature branch off of master and when ready, submit a merge request. Make branch names and commits descriptive. A merge request should solve one problem, not many. 

## Licensing

In addition to CALDERA's open source capabilities, MITRE maintains several in-house CALDERA plugins that offer 
more advanced functionality. For more information, or to discuss licensing opportunities, please reach out to 
caldera@mitre.org or directly to [MITRE's Technology Transfer Office](https://www.mitre.org/about/corporate-overview/contact-us#technologycontact).

## Related MITRE Work

[BRAWL Game](https://github.com/mitre/brawl-public-game-001) - Data set created by the BRAWL project representing
one CALDERA operation with data collected by Microsoft Sysmon and other sensors.

[CASCADE](https://github.com/mitre/cascade-server) - Prototype blue team analysis tool to automate investigative work.

## Acknowledgements

[Atomic Red Team](https://github.com/redcanaryco/atomic-red-team)
