What is an operation?
=================

An operation is started when you point an adversary at a group and have it run all capable abilities. 

An operation can be started with a number of optional configurations:

* **Planner**: You can select which logic library - or [planner](What-is-a-planner.md) - you would like to use.
* **Fact source**: You can attach a [source of facts](What-is-a-fact.md) to an operation. This means the operation will start with "pre-knowledge" of the facts, which it can use to fill in variables inside the abilities. 
* **Jitter**: Agents normally check in with CALDERA every 60 seconds. Once they realize they are part of an active operation, agents will start checking in according to the jitter time, which is by default 2/8. This fraction tells the agents that they should pause between 2 and 8 seconds (picked at random each time an agent checks in) before using the next ability. 