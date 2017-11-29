# CALDERA

CALDERA is an automated adversary emulation system that performs post-compromise adversarial behavior within
enterprise networks. It generates plans during operation using a [planning system](#planning-system) and a
pre-configured adversary model based on the
[Adversarial Tactics, Techniques & Common Knowledge](https://attack.mitre.org) (ATT&CK™) project. 
These features allow CALDERA to dynamically operate over a set of systems using variable behavior,
which better represents how human adversaries perform operations than systems that follow 
prescribed sequences of actions.

CALDERA is useful for defenders who want to generate real data that represents how an adversary 
would typically behave within their networks. Since CALDERA's knowledge about a network is gathered
during its operation and is used to drive its use of techniques to reach a goal, defenders can get a glimpse into
how the intrinsic security dependencies of their network allow an adversary to be successful. CALDERA 
is useful for identifying new data sources, creating and refining behavioral-based intrusion detection analytics, 
testing defenses and security configurations, and generating experience for training.

## How CALDERA is Used

Demo coming soon

## Architecture

CALDERA consists of:

* Server
  * Planner - Decision engine allowing CALDERA to chose actions
    * Attacker Model - Actions available based on ATT&CK
    * World Model - Representation of the environment
  * Execution Engine - Drives actuation of techniques and updates the database
  * Database - Stores knowledge learned about the environment
  * HTTP Server
* Clients
  * Agent - Client on endpoint systems used for communication
  * RAT - Remote access tool used during operations to emulate adversary behavior

![CALDERA Architecture](https://user-images.githubusercontent.com/379437/33388868-28491af2-d4ff-11e7-8ba4-b1c475b0c3ca.png)

### Planning System

CALDERA's planning system allows it to "decide" the next best action to take based upon its current
knowledge of the environment and the actions available at a given point in time. CALDERA's attacker model is 
represented by pre-configured ATT&CK-based techniques that have been logically encoded
with pre and post conditions allowing CALDERA to chain together sequences of actions to reach an 
objective state.

![CALDERA Planner Algorithm](https://user-images.githubusercontent.com/379437/33388878-30673ebc-d4ff-11e7-84d1-79fdb719d467.png)

The system follows this algorithm:
1. Update the world state
2. Figure out all valid actions to execute
3. Construct plans that lead off with those actions, chain actions together by leveraging model
5. Run heuristic to determine best plan
6. Execute the first action in the best plan
6. Repeat

#### Extensibility

New techniques can be added to CALDERA without having to recompute new decision models because of how techniques are
logically defined. It is encouraged to develop new techniques and variations of techniques to better represent the 
variations in how adversaries can behave and contribute them back to the project.

## Requirements

Requirements are detailed in the [Requirements](docs/requirements.rst) documentation.

## Installation 

Detailed installation instructions are included in the [Installation](docs/installation.rst) documentation.

## Considerations and Limitations

The path chaining problems CALDERA's planning system is designed to solve are computationally intensive. 
While CALDERA's server does not have hardware requirements beyond a typical software developer's system, there are
limitations on the number of systems CALDERA can operate over before the planning time between actions will cause
significant delays or the system to fail. **Thus it is not recommended that CALDERA be used against sets of systems 
larger than 20.**

CALDERA performs real actions on systems when operating. If it is being used in a production network, beyond an 
isolated lab network, then care should be taken to inform any network security staff, administrators, or users who 
may be impacted prior to using CALDERA to deconflict any issues that may arise.

CALDERA uses other open source tools as part of its repository of techniques. Some of these tools
are categorized as penetration testing or security auditing tools. See [Security](SECURITY.md) for
more information.

CALDERA does not use or repurpose known adversary malware. It focuses on using adversary behavior documented
within ATT&CK, which can be employed in many different ways regardless of specific pieces of malware an adversary 
may use.

CALDERA does not emulate adversary command and control (C2) channels. The variation in adversary C2 protocols
and communication methods is vast and is considered out of scope.

CALDERA also does not use software exploitation. There are many free and commercial tools that can be used
to assess software weakness and exploitability. CALDERA should not be used for this purpose.

## Research

CALDERA is a MITRE research project and is an implementation of some of the ideas described in the following papers:

[Intelligent, Automated Red Team Emulation](https://dl.acm.org/citation.cfm?id=2991111)

[Analysis of Automated Adversary Emulation Techniques](https://dl.acm.org/citation.cfm?id=3140081)

## Related MITRE Work

[BRAWL Game](https://github.com/mitre/brawl-public-game-001) - Data set created by the BRAWL project representing
one CALDERA operation with data collected by Microsoft Sysmon and other sensors.

[CASCADE](https://github.com/mitre/cascade-server) - Prototype blue team analysis tool to automate investigative work.
