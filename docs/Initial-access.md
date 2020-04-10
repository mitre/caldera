Initial Access
================

CALDERA allows for easy initial access attacks, by leveraging the Access plugin. This guide will walk you through how
to fire off an initial access attack, as well as how to build your own. 

## Run an initial access technique

Start by deploying an agent locally. This agent will be your "assistant". It will execute any attack you feed it. You
could alternatively deploy the agent remotely, which will help mask where your initial access attacks are originating.

From the Access plugin, select your agent and either the initial access tactic or any pre-ATT&CK tactic. This will
filter the abilities. Select any ability within your chosen tactic.

Once selected, a pop-up box will show you details about the ability. You'll need to fill in values for any properties
your selected ability requires. Click OK when done. 

Finally, click to run the ability against your selected agent. The ability will be in one of 3 states: IN-PROGRESS, 
SUCCESS or FAILED. If it is in either of the latter two states, you can view the logs from the executed ability by
clicking on the star.

## Write an initial access ability

You can easily add new initial access or pre-ATT&CK abilities yourself.

### Create a binary

You can use an existing binary or write your own - in any language - to act as your payload. The binary itself should
contain the code to execute your attack. It can be as simple or complex as you'd like. It should accept parameters 
for any dynamic behaviors. At minimum, you should require a parameter for "target", which would be your intended IP 
address, FQDN or other target that your attack will run against. 

As an example, look at the scanner.sh binary used for conducting a simple NMAP scan:
```
#!/bin/bash

echo '[+] Starting basic NMAP scan'
nmap -Pn $1
echo '[+] Complete with module'
```
This binary simply echos a few log statements and runs an NMAP scan against the first parameter (i.e., the target) passed to it. 

### Create an ability

With your binary at hand, you can now create a new ability YML file inside the Access plugin (plugins/access/data/abilities/*).
Select the correct tactic directory (or create one if one does not exist). Here is what the YML file looks like for 
the scanner.sh binary:
```
---
- id: 567eaaba-94cc-4a27-83f8-768e5638f4e1
  name: NMAP scan
  description: Scan an external host for open ports and services
  tactic: technical-information-gathering
  technique:
    name: Conduct active scanning
    attack_id: T1254
  platforms:
    darwin,linux:
      sh:
        command: |
          ./scanner.sh #{target.ip}
        timeout: 300
        payloads:
          - scanner.sh
```
This is the same format that is used for other CALDERA abilities, so refer to the "Learning the terminology" doc page
for a run-through of all the fields. 

### Run the ability

With your ability YML file loaded, restart CALDERA and head to the Access plugin to run it.