# CALDERA

CALDERA is an automated adversary emulation system, built on the [MITRE ATT&CK™ framework](https://attack.mitre.org/).

CALDERA works by attaching abilities to an adversary and running the adversary in an operation. Full documentation for this system can be found in [the wiki](https://github.com/mitre/caldera/wiki).

## Pardon our dust!
CALDERA is an actively developed project, and many features are subject to change. In April 2019 we released a new version of CALDERA that made much of our old documentation obsolete, leading to some confusion over CALDERA's current capabilities. For more information on this change, please read our [CALDERA 2.0](https://github.com/mitre/caldera/wiki/CALDERA-2.0) page on the wiki.

## Requirements

* Python 3.5.3+
* Google Chrome is our only supported/tested browser

Additionally, this code (the C2 server) is intended to be run on Linux or MacOS. 
The agents - which connect to the C2 - can run on Windows, Linux and MacOS.

## Installation

Start by cloning this repository recursively, passing the desired version/release in x.x.x format. This will pull all available [plugins](https://github.com/mitre/caldera/wiki/What-is-a-plugin). 
```
git clone --branch x.x.x https://github.com/mitre/caldera.git --depth 1 --recursive
```
> Clone the master branch - recursively - if you want to use bleeding-edge code

From the root of this project, install the PIP requirements.
```
pip install -r requirements.txt
```

Then start the server.
```
python server.py
```

## Quick start

To understand CALDERA, it helps to run an operation. Below are pre-built missions you can execute to understand 
the system. The missions assume CALDERA is running locally.

### Mission #1: Nosy Neighbor

> Perform reconnaissance on a compromised laptop. Your employer needs a list of the laptop user’s preferred WIFI 
networks. Grab this list, collecting anything else along the way, then knock the user offline. Finally, get out. Quickly. Leave no trace. There is one caveat: the laptop’s AV scans the machine in full every minute. You must complete this mission in 
less than 60 seconds. 

Start a [54ndc47 agent](https://github.com/mitre/caldera/wiki/Plugins-sandcat) on the same computer as CALDERA. Do this by opening a terminal and pasting in the correct
delivery command for your operating system. You should be welcomed by a log message indicating the agent has sent
a "beacon" to CALDERA.

Move to a browser, at 127.0.0.1:8888, logging in with the credentials admin:admin. 
Click into the [Chain plugin](https://github.com/mitre/caldera/wiki/Plugins-chain) and use the "Operations" section to fire off an operation using the "nosy neighbor" 
adversary and the my_group group. Fill in an operation name but leave all other fields at their defaults.

Once the operation is complete, compare the execution time of the first and last commands. Was
the mission a success? Did the adversary run without a trace? Can you figure out why the 
abilities are being run in the order they are?

### Mission #2: File Hunter

> A laptop containing secret, sensitive files has been compromised. Scan the computer for files which match
the file extensions (.txt and .yml) the sensitive files are known to have. Then steal the files.

Similar to mission #1, start a 54ndc47 agent and confirm it "beacons" back to CALDERA. 

Once confirmed, move to a browser at 127.0.0.1 and click into Chain mode. Click into the "facts"
section and examine the available [fact sources](https://github.com/mitre/caldera/wiki/What-is-a-fact).
Note that the _built-in_ fact source contains the file extensions that you will be hunting for.

Click into the "operations" section and start a new operation. Choose the "hunter" adversary
and ensure that you select the fact source of extensions. By feeding these facts into the operation, 
the adversary profile chosen (file hunter) will utilize them inside its abilities.

Did the operation find the sensitive files? How many? Can you determine what controls the number of files it looks for?

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
