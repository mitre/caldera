[![Release](https://img.shields.io/badge/dynamic/json?color=blue&label=Release&query=tag_name&url=https%3A%2F%2Fapi.github.com%2Frepos%2Fmitre%2Fcaldera%2Freleases%2Flatest)](https://github.com/mitre/caldera/releases/latest)
[![Build Status](https://travis-ci.com/mitre/caldera.svg?branch=master)](https://travis-ci.com/mitre/caldera)
[![codecov](https://codecov.io/gh/mitre/caldera/branch/master/graph/badge.svg)](https://codecov.io/gh/mitre/caldera)
[![Documentation Status](https://readthedocs.org/projects/caldera/badge/?version=stable)](http://caldera.readthedocs.io/?badge=stable)

# CALDERA

*Full documentation, training and use-cases can be found [here](https://caldera.readthedocs.io/en/latest/)*

CALDERA is a cyber security framework designed to easily run autonomous breach-and-simulation exercises. It can also be used to run manual red-team engagements or automated incident response.

It is built on the [MITRE ATT&CK™ framework](https://attack.mitre.org/) and is an active research project at MITRE.

The framework consists of two components:

1) **The core system**. This is the framework code, consisting of what is available in this repository. Included is 
an asynchronous command-and-control (C2) server with a REST API and a web interface. 
2) **Plugins**. These are separate repositories that hang off of the core framework, providing additional functionality. 
Examples include agents, GUI interfaces, collections of TTPs and more. 

## Plugins
- **[Access](https://github.com/mitre/access)** 
- **[Atomic](https://github.com/mitre/atomic)** 
- **[Builder](https://github.com/mitre/builder)** 
- **[Compass](https://github.com/mitre/compass)** 
- **[GameBoard](https://github.com/mitre/gameboard)** 
- **[Human](https://github.com/mitre/human)** 
- **[Manx](https://github.com/mitre/manx)** 
- **[Mock](https://github.com/mitre/mock)** 
- **[Response](https://github.com/mitre/response)** 
- **[Sandcat](https://github.com/mitre/sandcat)** 
- **[SSL](https://github.com/mitre/SSL)** 
- **[Stockpile](https://github.com/mitre/stockpile)** 
- **[Training](https://github.com/mitre/training)** 

## Requirements

These requirements are for the computer running the core framework:

* Any Linux or MacOS
* Python 3.6.1+ (with Pip3)
* Google Chrome is our only supported browsers
* Recommended hardware to run on is 8GB+ RAM and 2+ CPUs

## Installation

Start by cloning this repository recursively, passing the desired version/release in x.x.x format. This will pull in all available plugins. If you clone master - or any non-release branch - you may experience bugs.
```
git clone https://github.com/mitre/caldera.git --recursive --branch x.x.x 
```

Next run the install.sh script. See the i[nstall docs](https://caldera.readthedocs.io/en/latest/Install-script.html) for supported operating-systems.
```
./install.sh
```

Finally, start the server. 
```
python server.py
```
You can now navigate to 127.0.0.1:8888 in a browser and log in with either red team (red:admin) or blue team (blue:admin) credentials. Once you have everything running, we highly recommend going through the Training plugin to learn the ins-and-outs of the framework.

> There is also a [Docker image](https://caldera.readthedocs.io/en/latest/Docker-deployment.html) for CALDERA.

## Video tutorial

Watch the [following video](https://www.youtube.com/watch?v=_mVGjqu03fg) for a brief run through of how to run your first operation. 

## Contributing
Refer to our [contributor documentation](CONTRIBUTING.md)

## Licensing

In addition to CALDERA's open source capabilities, MITRE maintains several in-house CALDERA plugins that offer 
more advanced functionality. For more information, or to discuss licensing opportunities, please reach out to 
caldera@mitre.org or directly to [MITRE's Technology Transfer Office](https://www.mitre.org/about/corporate-overview/contact-us#technologycontact).
