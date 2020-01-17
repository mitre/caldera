What is an ability?
===============

An ability is a specific ATT&CK technique implementation (procedure). Abilities are stored in YML format and are loaded into CALDERA each time it starts. 

All abilities are stored inside the [Stockpile plugin](Plugins-stockpile.md), along with [adversary](What-is-an-adversary.md) profiles which use them. 

Here is a sample ability:
```
- id: 9a30740d-3aa8-4c23-8efa-d51215e8a5b9
  name: Scan WIFI networks
  description: View all potential WIFI networks on host
  tactic: discovery
  technique:
    attack_id: T1016
    name: System Network Configuration Discovery
  platforms:
    darwin:
      sh:
        command: |
          ./wifi.sh scan
        payload: wifi.sh
    linux:
      sh:
        command: |
          ./wifi.sh scan
        payload: wifi.sh
    windows:
      psh,pwsh:
        command: |
          .\wifi.ps1 -Scan
        payload: wifi.ps1
```

Things to note:
* Each ability has a random UUID id
* Each ability requires a name, description, ATT&CK tactic and technique information
* Each ability requires a platforms list, which should contain at least 1 block for a supported operating system (platform). Currently, abilities can be created for darwin, linux or windows. 

For each platform, there should be a list of executors. Currently Darwin and Linux platforms can use sh and Windows can use psh (PowerShell), cmd (command prompt) or pwsh (open-source PowerShell core).

Each platform block consists of a:
* command (required)
* payload (optional)
* cleanup (optional)
* parsers (optional)

**Command**: A command can be 1-line or many and should contain the code you would like the ability to execute. The command can (optionally) contain variables, which are identified as #{variable}. In the example above, there is one variable used, #{files}. A variable means that you are letting CALDERA fill in the actual contents. CALDERA has 3 global variables: 

* #{server} references the FQDN of the CALDERA server itself. Because every agent may know the location of CALDERA differently, using the #{server} variable allows you to let the system determine the correct location of the server.
* #{group} is the group a particular agent is a part of. This variable is mainly useful for lateral movement, where your command can start an agent within the context of the agent starting it. 
* #{location} is the location of the agent on the client file system. 
* #{paw} is the unique identifier - or paw print - of the agent

Global variables can be identified quickly because they will be single words.

You can use these global variables freely and they will be filled in before the ability is used. Alternatively, you can write in your own variables and supply CALDERA with facts to fill them in. 

**Payload**: A comma-separated list of files which the ability requires in order to run. In the windows executor above, the payload is wifi.ps1. This means, before the ability is used, the agent will download wifi.ps1 from CALDERA. If the file already exists, it will not download it. You can store any type of file in the payload directories of any plugin.

> Did you know that you can assign functions to execute on the server when specific payloads are requested for download? An example of this is the sandcat.go file. Check the plugins/sandcat/hook.py file to see how special payloads can be handled.

Payloads can be stored as regular files or you can xor (encode) them so the anti-virus on the server-side does not pick them up. To do this, run the app/utility/payload_encoder.py against the file to create an encoded version of it. Then store and reference the encoded payload instead of the original.

> The payload_encoder.py file has a docstring which explains how to use the utility.

**Cleanup**: An instruction that will reverse the result of the command. This is intended to put the computer back into the state it was before the ability was used. For example, if your command creates a file, you can use the cleanup to remove the file. Cleanup commands run after an operation, in the reverse order they were created. Cleaning up an operation is also optional, which means you can start an operation and instruct it to skip all cleanup instructions. 

Cleanup is not needed for abilities, like above, which download files through the payload block. Upon an operation completing, all payload files will be removed from the client (agent) computers.

**Parsers**: A list of parsing modules which can parse the output of the command into new facts. Interested in this topic? Check out [how CALDERA makes decisions](How-CALDERA-makes-decisions.md) which goes into detail about parsers. 

Abilities can also make use of two CALDERA REST API endpoints, [file upload and file download](File-upload-and-download.md).