Objectives
============

As part of ongoing efforts to increase the capabilities of CALDERA's Planners, the team has implemented 
Objectives. Objectives are collections of fact targets, called Goals, which can be tied to Adversaries. 
When an Operation starts, the Operation will store a copy of the Objective linked to the chosen Adversary, 
defaulting to a base Goal of "running until no more steps can be run" if no Objective can be found. During 
the course of an Operation, every time the planner moves between buckets, the current Objective status is 
evaluated in light of the current knowledge of the Operation, with the Operation completing should all 
goals be met.

### Objectives

The Objective object can be examined at `app/objects/c_objective.py`. 

Objective objects utilize four attributes, documented below:

* **id**: The id of the Objective, used for referencing it in Adversaries
* **name**: The name of the Objective
* **description**: A description for the Objective
* **goals**: A list of individual Goal objects

> For an Objective to be considered complete, all Goals associated with it must be achieved during an 
Operation

At the moment, Objectives can be added to CALDERA by creating Objective YAML files, such as the one 
shown below, or through Objectives web UI modal:

```yaml
id: 7ac9ef07-defa-4d09-87c0-2719868efbb5
name: testing
description: This is a test objective that is satisfied if it finds a user with a username of 'test'
goals:
  - count: 1
    operator: '='
    target: host.user.name
    value: 'test'
``` 

Objectives can be tied to Adversaries either through the Adversaries web UI, or by adding a line similar 
to the following to the Adversary's YAML file:

```yaml
objective: 7ac9ef07-defa-4d09-87c0-2719868efbb5
```

### Goals

Goal objects can be examined at `app/objects/secondclass/c_goal.py`. Goal objects are handled as 
extensions of Objectives, and are not intended to be interacted with directly.

Goal objects utilize four attributes, documented below:

* **target**: The fact associated with this goal, i.e. `host.user.name`
* **value**: The value this fact should have, i.e. `test`
* **count**: The number of times this goal should be met in the fact database to be satisfied, defaults 
to infinity (2^20)
* **operator**: The relationship to validate between the target and value. Valid operators include:
    * **`<`**: Less Than
    * **`>`**: Greater Than
    * **`<=`**: Less Than or Equal to
    * **`>=`**: Greater Than or Equal to
    * **`in`**: X in Y
    * **`*`**: Wildcard - Matches on existence of `target`, regardless of `value`
    * **`==`**: Equal to        

Goals can be input to CALDERA either through the Objectives web UI modal, or through Objective YAML files,
 where they can be added as list entries under goals. In the example of this below, the Objective 
 references two Goals, one that targets the specific username of `test`, and the other that is satisfied 
 by any two acquired usernames:

```yaml
goals:
  - count: 1
    operator: '='
    target: host.user.name
    value: 'test'
  - count: 2
    operator: '*'
    target: host.user.name
    value: 'N/A'
``` 