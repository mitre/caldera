[![Release](https://img.shields.io/badge/dynamic/json?color=blue&label=Release&query=tag_name&url=https%3A%2F%2Fapi.github.com%2Frepos%2Fmitre%2Fcaldera%2Freleases%2Flatest)](https://github.com/mitre/caldera/releases/latest)
[![Build Status](https://travis-ci.com/mitre/caldera.svg?branch=master)](https://travis-ci.com/mitre/caldera)
[![Documentation Status](https://readthedocs.org/projects/caldera/badge/?version=stable)](http://caldera.readthedocs.io/?badge=stable)

**[Sandcat](https://github.com/mitre/sandcat)**|**[Mock](https://github.com/mitre/mock)**|**[Terminal](https://github.com/mitre/terminal)**|**[SSL](https://github.com/mitre/SSL)**|**[Stockpile](https://github.com/mitre/stockpile)**|**[Atomic](https://github.com/mitre/atomic)**|**[Compass](https://github.com/mitre/compass)**|**[Access](https://github.com/mitre/access)**|**[Response](https://github.com/mitre/response)**
:-----:|:-----:|:-----:|:-----:|:-----:|:-----:|:-----:|:-----:|:-----:
[![Build Status](https://travis-ci.com/mitre/sandcat.svg?branch=master)](https://travis-ci.com/mitre/sandcat)|[![Build Status](https://travis-ci.com/mitre/mock.svg?branch=master)](https://travis-ci.com/mitre/mock)|[![Build Status](https://travis-ci.com/mitre/terminal.svg?branch=master)](https://travis-ci.com/mitre/terminal)|[![Build Status](https://travis-ci.com/mitre/ssl.svg?branch=master)](https://travis-ci.com/mitre/ssl)|[![Build Status](https://travis-ci.com/mitre/stockpile.svg?branch=master)](https://travis-ci.com/mitre/stockpile)|[![Build Status](https://travis-ci.com/mitre/caltack.svg?branch=master)](https://travis-ci.com/mitre/atomic)|[![Build Status](https://travis-ci.com/mitre/compass.svg?branch=master)](https://travis-ci.com/mitre/compass)|[![Build Status](https://travis-ci.com/mitre/access.svg?branch=master)](https://travis-ci.com/mitre/access)|[![Build Status](https://travis-ci.com/mitre/response.svg?branch=master)](https://travis-ci.com/mitre/response)

# CALDERA

*Full documentation, training and use-cases can be found [here](https://caldera.readthedocs.io/en/latest/)*

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

Start by cloning this repository recursively, passing the desired version/release in x.x.x format. This will pull in all available plugins.
```
git clone https://github.com/mitre/caldera.git --recursive --branch x.x.x 
```

Next run the install.sh script. Replace "ubuntu" with your operating-system. See the i[nstall docs](https://caldera.readthedocs.io/en/latest/Install-script.html) for supported operating-systems.
```
./install.sh --ubuntu
```

Finally, start the server. 
```
python server.py
```
You can now navigate to 127.0.0.1:8888 in a browser and log in with either red team (red:admin) or blue team (blue:admin) credentials. 

> There is also a [Docker image](https://caldera.readthedocs.io/en/latest/Docker-deployment.html) for CALDERA.

## Video tutorial

Watch the following video for a brief run through of how to run your first operation. 

[![IMAGE ALT TEXT HERE](https://img.youtube.com/vi/GukTj-i3UDg/0.jpg)](https://www.youtube.com/watch?v=GukTj-i3UDg)

## Developers

Want to contribute to this project? We use the basic feature branch GIT flow. Fork this repository and create a feature branch off of master and when ready, submit a merge request. Make branch names and commits descriptive. A merge request should solve one problem, not many. 

## Licensing

In addition to CALDERA's open source capabilities, MITRE maintains several in-house CALDERA plugins that offer 
more advanced functionality. For more information, or to discuss licensing opportunities, please reach out to 
caldera@mitre.org or directly to [MITRE's Technology Transfer Office](https://www.mitre.org/about/corporate-overview/contact-us#technologycontact).
