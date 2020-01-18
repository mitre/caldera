What is an operation?
=================

An operation is started when you point an adversary at a group and have it run all capable abilities. 

An operation can be started with a number of optional configurations:

* **Group**: Which collection of agents would you like to run against
* **Adversary**: Which adversary profile would you like to run
* **Run immediately**: Run the operation immediately or start in a paused state
* **Planner**: You can select which logic library - or [planner](What-is-a-planner.md) - you would like to use.
* **Fact source**: You can attach a [source of facts](What-is-a-fact.md) to an operation. This means the operation will start with "pre-knowledge" of the facts, which it can use to fill in variables inside the abilities. 
* **Trust**: Run against trusted agents only - or trusted and untrusted agents.
* **Autonomous**: Run autonomously or manually. Manual mode will ask the operator to approve or discard each command.
* **Phases**: Run the adversary normally, abiding by phases, or smash all phases into a single one.
* **Auto-close**: Automatically close the operation when there is nothing left to do. Alternatively, keep the operation for the max_time duration.
* **Obfuscators**: Select an obfuscator to encode each command with, before they are sent to the agents.
* **Jitter**: Agents normally check in with CALDERA every 60 seconds. Once they realize they are part of an active operation, agents will start checking in according to the jitter time, which is by default 2/8. This fraction tells the agents that they should pause between 2 and 8 seconds (picked at random each time an agent checks in) before using the next ability. 
* **Visibility**: How visible should the operation be to the defense. Defaults to 51 because each ability defaults to a visibility of 50. Abilities with a higher visibility than the operation visibility will be skipped.
