Plugin library
============

Here you'll get a run-down of all open-source plugins, all of which can be found in the plugins/ directory as separate 
GIT repositories. 

## Sandcat (54ndc47)

The Sandcat plugin, otherwise known as 54ndc47, is the default agent that CALDERA ships with. 
54ndc47 is written in GoLang for cross-platform compatibility. 

54ndc47 agents require network connectivity to CALDERA at port 8888.

### Deploy 

To deploy 54ndc47, use one of the built-in delivery commands which allows you to run the agent on any operating system. 
Each of these commands downloads the compiled 54ndc47 executable from CALDERA and runs it immediately. Find
the commands on the Sandcat plugin tab.

Once the agent is running, it should show log messages when it beacons into CALDERA.

> If you have GoLang installed on the CALDERA server, each time you run one of the delivery commands above, 
the agent will re-compile itself dynamically and it will change it's source code so it gets a different file 
hash (MD5) and a random name that blends into the operating system. This will help bypass file-based signature detections.

### Options

When deploying a 54ndc47 agent, there are optional parameters you can use when you start the executable:

* **Server**: This is the location of CALDERA. The agent must have connectivity to this host/port. 
* **Group**: This is the group name that you would like the agent to join when it starts. The group does not have to exist. A default group of my_group will be used if none is passed in.
* **v**: Use `-v` to see verbose output from sandcat.  Otherwise, sandcat will run silently. 

#### Customizing Default Options & Execution Without CLI Options

It's possible to customize the default values of these options when pulling Sandcat from the CALDERA server.  
This is useful if you want to hide the parameters from the process tree. You can do this by passing the values
in as headers instead of as parameters.

For example, the following will download a linux executable that will use `http://10.0.0.2:8888` as the server address 
instead of `http://localhost:8888`.

```
curl -sk -X POST -H 'file:sandcat.go' -H 'platform:linux' -H 'server:http://10.0.0.2:8888' http://localhost:8888/file/download > sandcat.sh
```

## Mock 

The Mock plugin adds a set of simulated agents to CALDERA and allows you to run complete operations without hooking any other computers up to your server. 

These agents are created inside the `conf/agents.yml` file. They can be edited and you can create as many as you'd like. A sample agent looks like:
```
- paw: 1234
  username: darthvader
  host: deathstar
  group: simulation
  platform: windows
  location: C:\Users\Public
  enabled: True
  privilege: User
  c2: HTTP
  exe_name: sandcat.exe
  executors:
    - pwsh
    - psh
```

After you load the mock plugin and restart CALDERA, all simulated agents will appear as normal agents in the Chain plugin GUI and can be used in any operation.

## Terminal

The terminal plugin adds reverse-shell capability to CALDERA, along with a TCP-based agent called Manx.

When this plugin is loaded, you'll get access to a new GUI page which allows you to drop reverse-shells on target hosts 
and interact manually with the hosts. 

You can use the terminal emulator on the Terminal GUI page to interact with your sessions. 

## Stockpile

The stockpile plugin adds a few components to CALDERA:

* Abilities
* Adversaries
* Planner
* Facts

These components are all loaded through the data/* directory.

## Response

The response plugin is an autonomous incident response plugin, which can fight back against adversaries
on a compromised host.

## Compass

Create visualizations to explore TTPs. Follow the steps below to create your own visualization:

1. Click 'Generate Layer'
1. Click '+' to open a new tab in the navigator
1. Select 'Open Existing Layer'
1. Select 'Upload from local' and upload the generated layer file

Compass leverages ATT&CK Navigator, for more information see: [https://github.com/mitre-attack/attack-navigator](https://github.com/mitre-attack/attack-navigator)

## Caltack

The caltack plugin adds the public MITRE ATT&CK website to CALDERA. This is useful for deployments of CALDERA where an operator cannot access the Internet to reference the MITRE ATT&CK matrix.

After loading this plugin and restarting, the ATT&CK website is available from the CALDERA home page. Not all parts of the ATT&CK website will be available - but we aim to keep those pertaining to tactics and techniques accessible.

## SSL

The SSL plugin adds HTTPS to CALDERA. 
> This plugin only works if CALDERA is running on a Linux or MacOS machine. It requires HaProxy (>= 1.8) to be installed prior to using it.

When this plugin has been loaded, CALDERA will start the HAProxy service on the machine and then serve CALDERA at hxxps://[YOUR_IP]:8443, instead of the normal hxxp://[YOUR_IP]:8888.

CALDERA will **only** be available at https://[YOUR_IP]:8443 when using this plugin. All deployed agents should use the correct address to connect to CALDERA. 

## Atomic

The Atomic plugin imports all Red Canary Atomic tests from their open-source GitHub repository.

## GameBoard

The GameBoard plugin allows you to monitor both red-and-blue team operations. The game tracks points for both sides
and determines which one is "winning". 