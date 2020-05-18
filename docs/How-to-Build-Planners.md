How to Build Planners
================

For any desired planner decision logic not encapsulated in the default _batch_ planner (or any other existing planner), CALDERA requires that a new planner be implemented to encode such decision logic.

## Buckets

The cornerstone of how planners make decisions is centered on a concept we call 'buckets'. Buckets denote the planner's state machine and are intended to correspond to _buckets_ of CALDERA abilites. Within a planner, macro level decision control is encoded by specifying which buckets (i.e. states) follow other buckets, thus forming a bucket state machine. Micro level decisions are made within the buckets, by specifying any logic detailing which abilities to send to agents and when to do so.

CALDERA abilities are also tagged by the buckets they are in. By default, when abilites are loaded by CALDERA, they are tagged with the bucket of the ATT&CK technique they belong to. CALDERA abilities can also be tagged/untagged at will by any planner as well, before starting the operation or at any point in it. The intent is for the defined planner buckets to work with the abilities that have been tagged for that bucket, but this is by no means enforced.

## Creating a Planner

Lets dive in to creating a planner in order to see the level of flexibility and power found in the CALDERA planner component. For this example, we will implement a planner that will carry out the following state machine:

![privileged persistence sm screenshot](/priveleged_persistence_sm_screenshot.png)

The planner will consist of 5 buckets:  _Privilege Escalation_, _Collection_, _Persistence_, _Discovery_, and _Lateral Movemnent_. As implied by the state machine, this planner will use the underlying adversary abilities to attempt to spread to as many hosts as possible and establish persistence. If persistence is prevented by unsuccessful attempts to get required privilege access for a given host, then execute collection abilities immediately in case it loses access to the host.

We will create a python module called ```privileged_peristence.py``` and nest it under ```/app``` in the ```mitre/stockpile``` plugin.

First, lets build the static initialization of the planner:

```
class LogicalPlanner:

    def __init__(self, operation, planning_svc, stopping_conditions=()):
        self.operation = operation
        self.planning_svc = planning_svc
        self.stopping_conditions = stopping_conditions
        self.stopping_condition_met = False
        self.state_machine = ['privilege_escalation', 'persistence', 'discovery', 'lateral_movement']
        self.next_bucket = 'privilege_escalation'

```

Breaking this down:

```
    def __init__(self, operation, planning_svc, stopping_conditions=()):
        self.operation = operation
        self.planning_svc = planning_svc
        self.stopping_conditions = stopping_conditions
        self.stopping_condition_met = False
```
The ```__init__()``` method for a planner must take and store the required arguments for the ```operation``` instance, ```planning_svc``` handle, and any supplied ```stopping_conditions```.  Additionally ```self.stopping_condition_met``` is set to False to begin with.

```
        self.state_machine = ['privilege_escalation', 'persistence', 'discovery', 'lateral_movement']
```
The ```state_machine``` variable is a list enumerating the order of the planner state machine. Primarily used if the planner state machine is a simple cycle, which then we may be able to use a planning service utility that can then execute our planner's state machine for us by simply following the state machine order defined in this variable (see planning service utilities below). If the planner state machine is more complex than a simple cycle, which is the case for our planner, then we can still use this ```state_machine``` variable to define a base line state machine that we can refer back to in our decision logic; this will be demonstrated when we create the bucket (i.e. state) methods.

```
        self.next_bucket = 'privilege_escalation'
```
The ```next_bucket``` variable holds the next bucket to be executed, that is the next bucket (i.e. state) that the planner will enter and whose bucket method will control the planning logic until. Initially, we set ```next_bucket``` to the first bucket the planner will begin in. We will moidfy ```next_bucket``` from within our bucket methods in order to specify the next bucket to execute.

**_Additional Planner class variables_**
It is also important to note that a planner may define any required variables that it may need. For instance, many custom planners require information to be passed from one bucket (state) to another during execution. This is done simply by creating a class variable(s) to store information that will persist between bucket transitions and can be accessed within any bucket method.

Now, lets the define the planner's entrypoint method ```execute()```. ```execute()``` is where the planner starts and where any runtime initialization is done.

```
    async def execute(self):
        await self.privilege_escalation()
```
For our planner, not much is required in the ```execute()``` method other than calling the first bucket to be executed. However, any runtime initialization required for the planner can be done here. For instance, the creation of new buckets can be supported with the planning service ```add_ability_to_bucket()``` utility.

Finally, lets create our bucket methods, where all inter-bucket transitions and intra-bucket logic will be encoded. For every bucket (state) in our planner state machine, we must define a corresponding bucket method.

```
    async def privilege_escalation(self):
        await self.planning_svc.exhaust_bucket(self, 'privilege escalation', self.operation)
        successful = 
        if successful:
            self.next_bucket = 'persistence'
        else:
            self.next_bucket = 'collection'

    async def persistence(self):
        await self.planning_svc.exhaust_bucket(self, 'persistence', self.operation)
        self.next_bucket = await self.planning_svc.default_next_bucket('persistence', self.state_machine)

    async def collection(self):
        # prioritize collection abilities
        await self.planning_svc.exhaust_bucket(self, 'collection', self.operation)
        self.next_bucket = await self.planning_svc.default_next_bucket('collection', self.state_machine)

   async def discovery(self):
        # only do certain discovery abilities
        
        if discovered_agents:
            self.next_bucket = await self.planning_svc.default_next_bucket('discovery', self.state_machine)
        else:
            # planner will transtion from this bucket to being done
            self.next = None

    async def lateral_movement(self):
        await self.do_bucket('lateral-movement')
        self.next_bucket = await self.planning_svc.default_next_bucket('lateral_movement', self.state_machine)
```

Lets look at each of the bucket methods in detail:

```privilege_escalation()```

```persistence()```

```collection()```

```discovery()```

```lateral_movement()```


**_Additional Notes on ```privelged_persistance``` Planner_**
- You may have noticed that the _priveleged_persistence_ planner is only notionally more sophisticated than running certain default adversary profiles. This is correct. If you can find or create an adversary profile whose ability enumeration (i.e. order) can carry out your desired operational progression between abilities and can be executed in batch (by the default _batch_ planner) or in a sequentially atomic order (by _atmomic_ planner), it is advised to go that route. However, any decision logic above those simple planners will have to be implemented in a new planner.
- The _priveleged persistence_ planner did not have explicit logic to handle multiple agents


## Planning Service Utilities (that are very useful to custom planners)

```exhaust_bucket()```

```default_next_bucket()```

```add_ability_to_next_bucket()```

```execute_planner()```

```get_links()```

```get_cleanup_links()```

```check_stopping_conditions()```

```upgrade_stopping_conditions()```
