How to Build Agents
================

Building your own agent is a way to create a unique - or undetectable - footprint on compromised machines. Our
default agent, 54ndc47, is a full representation of what an agent can do. This agent is written in GoLang and offers
an extensible collection of command-and-control (C2) protocols, such as communicating over HTTP or GitHub Gist. You can
extend 54ndc47 by adding your own C2 protocols in place or you can follow this guide to create your own agent 
from scratch.

## Understanding the layers

Think about building an agent as writing layers. 

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
