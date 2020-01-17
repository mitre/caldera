[![Release](https://img.shields.io/badge/dynamic/json?color=blue&label=Release&query=tag_name&url=https%3A%2F%2Fapi.github.com%2Frepos%2Fmitre%2Fcaldera%2Freleases%2Flatest)](https://github.com/mitre/caldera/releases/latest)

**[Caldera](https://github.com/mitre/caldera)**|**[Sandcat](https://github.com/mitre/sandcat)**|**[Mock](https://github.com/mitre/mock)**|**[Terminal](https://github.com/mitre/terminal)**|**[SSL](https://github.com/mitre/SSL)**|**[Stockpile](https://github.com/mitre/stockpile)**|**[Caltack](https://github.com/mitre/caltack)**|**[Compass](https://github.com/mitre/compass)**
:-----:|:-----:|:-----:|:-----:|:-----:|:-----:|:-----:|:-----:
[![Build Status](https://travis-ci.com/mitre/caldera.svg?branch=master)](https://travis-ci.com/mitre/caldera)|[![Build Status](https://travis-ci.com/mitre/sandcat.svg?branch=master)](https://travis-ci.com/mitre/sandcat)|[![Build Status](https://travis-ci.com/mitre/mock.svg?branch=master)](https://travis-ci.com/mitre/mock)|[![Build Status](https://travis-ci.com/mitre/terminal.svg?branch=master)](https://travis-ci.com/mitre/terminal)|[![Build Status](https://travis-ci.com/mitre/ssl.svg?branch=master)](https://travis-ci.com/mitre/ssl)|[![Build Status](https://travis-ci.com/mitre/stockpile.svg?branch=master)](https://travis-ci.com/mitre/stockpile)|[![Build Status](https://travis-ci.com/mitre/caltack.svg?branch=master)](https://travis-ci.com/mitre/caltack)|[![Build Status](https://travis-ci.com/mitre/compass.svg?branch=master)](https://travis-ci.com/mitre/compass)

# CALDERA

CALDERA is an automated adversary emulation system, built on the [MITRE ATT&CK™ framework](https://attack.mitre.org/). It is currently an active research project at MITRE.

CALDERA works by attaching abilities to an adversary and running the adversary in an operation. Full documentation for this system can be found on [ReadTheDocs](https://caldera.readthedocs.io/en/latest/), as well as by clicking on the `Docs` tab within the C2 UI.

## Requirements

* Python 3.6.1+
* Google Chrome is our only supported/tested browser

Additionally, this code (the C2 server) is intended to be run on Linux or MacOS. 
The agents - which connect to the C2 - can run on Windows, Linux and MacOS.

## Installation

Start by cloning this repository recursively, passing the desired version/release in x.x.x format. This will pull all available [plugins](https://caldera.readthedocs.io/en/latest/What-is-a-plugin.html). 
```
git clone https://github.com/mitre/caldera.git --recursive --branch x.x.x 
```

Next install the PIP requirements
```
pip install -r requirements.txt
```
> Instead of running the step above, you could run the [auto-installer.sh](https://caldera.readthedocs.io/en/latest/Auto-install-script.html) script to automatically configure CALDERA in our recommended way. 

Finally, start the server
```
python server.py
```

## Video tutorial

Watch the following video for a brief run through of how to run your first operation. 

[![IMAGE ALT TEXT HERE](https://img.youtube.com/vi/GukTj-i3UDg/0.jpg)](https://www.youtube.com/watch?v=GukTj-i3UDg)

## Quick start

To understand CALDERA, it helps to run an operation. Below are pre-built missions you can execute to understand 
the system. The missions assume CALDERA is running locally.

### Mission #1: Nosy Neighbor

> Perform reconnaissance on a compromised laptop. Your employer needs a list of the laptop user’s preferred WIFI 
networks. Grab this list, collecting anything else along the way, then knock the user offline. Finally, get out. Quickly. Leave no trace. There is one caveat: the laptop’s AV scans the machine in full every minute. You must complete this mission in 
less than 60 seconds. 

Start a [54ndc47 agent](https://caldera.readthedocs.io/en/latest/Plugins-sandcat.html) on the same computer as CALDERA. Do this by opening a terminal and pasting in the correct
delivery command for your operating system. You should be welcomed by a log message indicating the agent has sent
a "beacon" to CALDERA.

Move to a browser, at 127.0.0.1:8888, logging in with the credentials admin:admin. 
Click into campaigns and use the "Operations" section to fire off an operation using the "nosy neighbor" 
adversary and the my_group group. Fill in an operation name but leave all other fields at their defaults.

Once the operation is complete, compare the execution time of the first and last commands. Was
the mission a success? Did the adversary run without a trace? Can you figure out why the 
abilities are being run in the order they are?

### Mission #2: File Hunter

> A laptop containing secret, sensitive files has been compromised. Scan the computer for files which match
the file extensions (.txt and .yml) the sensitive files are known to have. Then steal the files.

Similar to mission #1, start a 54ndc47 agent and confirm it "beacons" back to CALDERA. 

Once confirmed, move to a browser at 127.0.0.1 and click into the campaigns -> operations section and start a new operation, choosing the hunter adversary and the group my_group.

Did the operation find the sensitive files? How many? Can you determine how it determines which files are sensitive? Hint: you may want to read about [facts](https://caldera.readthedocs.io/en/latest/What-is-a-fact.html).

### Mission #3: Terminal

> You need to navigate through a compromised host but you fear an autonomous agent may draw too much attention. You need to use a traditional reverse-shell to gain manual shell access.

Inside CALDERA, enable the terminal plugin by updating the conf/default.yml file and restart the server.

Once confirmed, move to a browser at 127.0.0.1 and click into the plugins -> terminal section and deploy a terminal agent on a compromised host using the 1-line delivery commmands available. Then, refresh and check the sessions drop-down and you should see a new reverse-shell session. Select this session and use the UI to manually interact with the host.

Can you figure out how to deploy the reverse-shell by running a regular CALDERA operation?

## Developers

We use the basic feature branch GIT flow. Create a feature branch off of master and when ready, submit a merge 
request. Make branch names and commits descriptive. A merge request should solve one problem,
not many. 

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
