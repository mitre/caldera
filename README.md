# CALDERA

CALDERA is an automated adversary emulation system, built on the [MITRE ATT&CK™ framework](https://attack.mitre.org/), 
It gives a red-or-blue team operator the ability to easily emulate an adversary.

Python 3.5.3+ is required to run this system.

## Installation

Start by cloning this repository recursively. This will pull all available plugins. 
```
git clone https://github.com/mitre/caldera.git --recursive
```

From the root of this project, install the PIP requirements.
```
pip install -r requirements.txt
```

Then start the server.
```
python server.py
```

## Plugins

CALDERA is built using a plugin architecture on top of the core system (this repository). Plugins are 
separate git repositories that plug new features into the core system. Each plugin resides in the plugins
directory and contains a hook.py file, which the core system uses to "hook" the plugin. For more information 
on each plugin, refer to their respective README files.

Load plugins into the core system by listing them in the conf/local.yml file, then restart
CALDERA for them to become available. If a plugin specifies any additional dependencies, they will need to 
be installed before using it.

## Terminology

CALDERA works by attaching abilities to an adversary and running the adversary in an operation. 

* **Ability**: A specific task or set of commands mapped to ATT&CK Tactics and Techniques, written in any language
* **Fact**: An indicator of compromise (IOC), found on a computer, which can be used inside an ability
* **Adversary**: A threat profile that contains a set of abilities, making it easy to form repeatable operations 
* **Agent**: An individual computer running a CALDERA agent, such as the [54ndc47 plugin](https://github.com/mitre/sandcat)
* **Group**: A collection of agents
* **Operation**: A start-to-finish execution of an adversary profile against a group

CALDERA ships with a few pre-built abilities and adversaries with the [Stockpile plugin](https://github.com/mitre/stockpile), 
but it's easy to add your own. 

## Getting started

To understand CALDERA, it helps to run an operation. Below is a pre-built mission you can execute to understand 
the system. This mission assumes CALDERA is running locally.

### Mission #1: Nosy Neighbor

> Perform reconnaissance on a compromised laptop. Your employer needs a list of the laptop user’s preferred WIFI 
networks. Grab this list, collecting anything else along the way, then get out. Quickly. Leave no trace. 
There is one caveat: the laptop’s AV scans the machine in full every minute. You must complete this mission in 
less than 60 seconds. 

Start a 54ndc47 agent on the same computer as CALDERA. Do this by opening a terminal and pasting in the correct
delivery command your operating system. You should be welcomed by a log message indicating the agent has sent
a "beacon" to CALDERA.

**OSX**:
```
while true; do curl -sk -X POST -H 'file:sandcat-darwin' http://localhost:8888/file/download > /tmp/sandcat-darwin && chmod +x /tmp/sandcat-darwin && /tmp/sandcat-darwin http://localhost:8888 my_group; sleep 60; done
```

**Linux**:
```
while true; do curl -sk -X POST -H 'file:sandcat-linux' http://localhost:8888/file/download > /tmp/sandcat-linux && chmod +x /tmp/sandcat-linux && /tmp/sandcat-linux http://localhost:8888 my_group; sleep 60; done
```

**Windows**:
```
while($true) {$url="http://localhost:8888/file/download";$wc=New-Object System.Net.WebClient;$wc.Headers.add("file","sandcat.exe");$output="C:\Users\Public\sandcat.exe";$wc.DownloadFile($url,$output);C:\Users\Public\sandcat.exe http://localhost:8888 my_group; sleep 60}
```

Move to a browser, at http://127.0.0.1:8888, logging in with the credentials admin:admin. 
Click into the Chain plugin and use the "Operations" section to fire off an operation using the "nosy neighbor" 
adversary and the my_group group. Fill in an operation name but leave all other fields at their defaults.

Once the operation is complete, compare the execution time of the first and last commands. Was
the mission a success? Did the adversary run without a trace? Can you figure out why the 
abilities are being run in the order they are?

## Versions

Bleeding-edge code can be run by using the latest master branch source code. Stable versions are tagged
by major.minor.bugfix numbers and can be used by cloning the appropriate tagged version:
```
git clone --branch 2.1.0 https://github.com/mitre/caldera.git --recursive
```

Check the GitHub releases for the most stable release versions.

> **IMPORTANT**: The core system relies on plugins (git submodules). If you are unfamiliar with this concept and want 
to run the bleeding-edge code, a "git pull" on this code will likely not be sufficient. The easiest way to run bleeding-edge
code is to recursively re-clone all of CALDERA when you want to update it.

### GIT flow

We use the basic feature branch GIT flow. Create a feature branch off of master and when ready, submit a merge 
request. Make branch names and commits descriptive. A merge request should solve one problem,
not many. 



## Licensing

In addition to CALDERA's open source capabilities, MITRE maintains several in-house CALDERA plugins that offer 
more advanced functionality. For more information, or to discuss licensing opportunities, please reach out to 
caldera@mitre.org or directly to MITRE's Technology Transfer Office at 
https://www.mitre.org/about/corporate-overview/contact-us#technologycontact.

## Related MITRE Work

[BRAWL Game](https://github.com/mitre/brawl-public-game-001) - Data set created by the BRAWL project representing
one CALDERA operation with data collected by Microsoft Sysmon and other sensors.

[CASCADE](https://github.com/mitre/cascade-server) - Prototype blue team analysis tool to automate investigative work.

## Acknowledgements

[Atomic Red Team](https://github.com/redcanaryco/atomic-red-team)
