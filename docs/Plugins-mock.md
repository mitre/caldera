Plugin: mock
==========

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

To simulate an operation, you can create a new scenario, or edit one. Scenario files link groups of mock'd ability responses together, and can be found in `conf/scenarios`. An excerpt of the hunter scenario can be found below:
```
name: hunter
type: advanced
responses:
  #whoami
  - ability_id: c0da588f-79f0-4263-8998-7496b1a40596
  #create staging directory
  - ability_id: 6469befa-748a-4b9c-a96d-f191fde47d89
  ...
```

Each ability_id entry under responses correlates to a specific simulated response file. These simulated response files can specify custom responses for each agent, indexed by the `paw` value, by filling out the appropriate file, which should be stored in `data/[scenario]`. A mock ability response (`data/hunter/c0da588f-79f0-4263-8998-7496b1a40596.yml`) looks like:
```
paws:
  - paw: 1234
    variables:
      - trait: default
        value: default
        status: 0
        response: |
          darthvader
  - paw: 4321
    variables:
      - trait: default
        value: default
        status: 0
        response: |
          redleader
  ...
```

There are three things to keep in mind when working with the response files:
1. The system is set up so that not only default responses per agent can be configured, but also that by adding additional entries, custom responses based on facts provided in the link issued to the mock agents (link.fact.trait=value). Please note that a default entry must always exist. 
2. It is possible to spawn a new agent as part of the response. This is accomplished by setting the response value equal to `|SPAWN|`, which mock will use as a flag to try to spawn a mock agent on the target of the command with the `|SPAWN|` response. 
3. Finally, make sure when using mock scenarios to load the proper scenario data via the UI, as only 'hunter' is loaded by default. 

Please note that if you run an operation with simulated agents and you have not mocked out the responses, the mock plugin will treat the response as empty. 