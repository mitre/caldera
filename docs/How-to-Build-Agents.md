How to Build Agents
================

Building your own agent is a way to create a unique - or non-detectable - footprint on compromised machines. Our
default agent, 54ndc47, is a full representation of what an agent can do. This agent is written in GoLang and offers
an extensible collection of command-and-control (C2) protocols, such as communicating over HTTP or GitHub Gist. You can
extend 54ndc47 by adding your own C2 protocols in place or you can follow this guide to create your own agent 
from scratch.

## Types of agents

There are 2 unique types of agents. Determining which one you want is your first step:

1) Active - a direct communication between agent-and-server. HTTP communication is an example.
2) Passive - an indirect communication between agent-and-server. Using a trusted 3rd party, like GitHub Gists, 
is an example. 

## Understanding the layers

No matter which type of agent you write, think about it as creating layers.

### Layer 1: Ping

The ping layer simply forms a communication channel that can ping to the server and confirm a connection. This ping
should send a 1-time "profile" to the server, containing data that describes the compromised host:

### Layer 2: Instruction

The instruction layer is where the agent asks the server for instructions, executes a given command, and sends
the results back to the server.

### Layer 3: Payload

The payload layer builds on the prior layer by actuating on the payload property that is included in each instruction. 
Instructions can optionally include a payload, which instructions the agent to download the given binary before
executing the command. Implementing this allows you to take advantage of instructions with a payload.

### Layer 4: Control

The control layer applies the configuration properties that are part of every instruction. These properties, like 
sleep time, are meant to trigger specific actions on the agent. These properties are configured dynamically from 
the server's agent modal on the GUI and are picked up by an agent upon each beacon. 

## Additional concepts

As the layers are being developed, the author should consider a few important details:

* Delivery: How do you plan on starting this agent?
* Detection: How easy is this agent to detect? Should you build in protections? What about persistence mechanisms?

## Building an active agent

Start by getting a feel for the HTTP(S) agent endpoints, which are located in the rest_api.py module.
```
POST  /ping 
POST  /instructions
*     /file/download
POST  /file/upload
```

Keep in mind, you can create new endpoint addresses by simply copy/pasting the endpoint definitions with new addresses. 
For example, if you were concerned that the /ping address could be detected, you could add the following line to
the rest_api.py:*enable* function:
```
self.app_svc.application.router.add_route('POST', '/you/cannot/find/me', self._ping)
```

### Layer 1

Start by writing a POST request to the /ping endpoint. This POST request requires no data to be sent in. You should 
receive a base64 encoded response, which equals "pong" when decoded.
```
> curl -s -X POST localhost:8888/ping | base64 --decode
... pong
```

### Layer 2

In your agent code, create a flat JSON dictionary of key/value pairs and ensure the following properties are included
as keys. Add values which correlate to the host your agent will be running on. 

#### Required properties

| Key           | Value  | Notes |
| :------------- |:------------- |:-------------|  
| paw           | A unique identifier for the host  | |
| server        | The location (IP or FQDN) of the C2 server    | |
| platform      | The operating system | The platform is evaluated against the platform field of each ability. Currently you can use windows, darwin or linux |

#### Optional properties

| Key           | Value  | Notes |
| :------------- |:------------- |:-------------|  
| group         | A group name you want to associate to this agent  | |
| host          | The hostname of the machine | |
| username      | The username running the agent | |
| architecture  | The architecture of the host. | |
| location      | The location of the agent on disk | |
| sleep         | The number of seconds to wait between beacons | |
| pid           | The process identifier of the agent | |
| executors     | A comma-separated string of executors allowed on the host | Executors are evaluated against the executor block of each ability. Currently, you can use sh, cmd, psh and pwsh |
| privilege     | The privilege level of the agent process, either User or Elevated | Privilege is evaluated against the optional privilege block of each ability file |
| exe_name      | The name of the agent binary file | |
| c2            | The C2-communication name | The c2 determines how to send instructions back to the agent. You should use "http" |
| watchdog      | The number of minutes to wait after a beacon cannot connect to the server before the agent kills itself | |

At this point, you're ready to make a POST request with the profile to the /instructions endpoint. You should get back
1) The recommended number of seconds to sleep before sending the next beacon
2) The recommended number of minutes to wait before killing the agent, once the server is unreachable (0 means infinite)
3) list of instructions - base64 encoded - which will be empty.
```
profile=$(echo '{"paw":"abc123","server":"http://127.0.0.1:8888","platform":"darwin"}' | base64)
curl -s -X POST -d $profile localhost:8888/instructions | base64 --decode
...{"sleep": 59, "watchdog": 0, "instructions": "[]"}
```

You can now navigate to the CALDERA UI, click into the agents tab and view your new agent. At this point, the agent
is fully ready to run operations. There are 2 more layers required to unlock the full potential of an operation - but
you can now run any ability that doesn't use a payload.
