What is an adversary?
=================

An adversary is a collection of abilities. 

The abilities inside an adversary can optionally be grouped into phases, which allows a user to choose which order they are executed. During an operation, each phase of the adversary is run in order. If there are multiple abilities in the same phase, CALDERA will determine which order to run them, based on the information it has gathered thus far in the operation. This decision making process is known as [the planner](What-is-a-planner.md).

An adversary can contain abilities which can be used on any platform (operating system). As an operation runs an adversary, CALDERA will match each ability to each agent and only send the matching ones to the agent.

Adversaries can be built either through the GUI or by adding YML files into data/adversaries/ which is in the Stockpile plugin.

If you build an adversary through a YML file, you can create a regular adversary or an adversary pack. 

### Regular adversary

A regular adversary is marked as visible (which means you can see it from the GUI) and contains a list of adversary packs, which correspond to ability pack IDs. A regular adversary can also (optionally) include a phases section, like an adversary pack. Here is an example of a regular adversary:
```
id: de07f52d-9928-4071-9142-cb1d3bd851e8
name: Hunter
description: Discover host details and steal sensitive files
visible: 1
packs:
  - 0f4c3c67-845e-49a0-927e-90ed33c044e0
  - 1a98b8e6-18ce-4617-8cc5-e65a1a9d490e
```

### Adversary pack

An adversary pack is the same as a regular adversary, except it is not marked as visible. A pack is intended to be a focused set of abilities, grouped into phases, that can be included into a regular adversary. Here is an example of an adversary pack:
```
id: 5d3e170e-f1b8-49f9-9ee1-c51605552a08
name: Collection
description: A collection adversary pack
visible: 0
phases:
  1:
    - 1f7ff232-ebf8-42bf-a3c4-657855794cfe #find company emails
    - d69e8660-62c9-431e-87eb-8cf6bd4e35cf #find ip addresses
    - 90c2efaa-8205-480d-8bb6-61d90dbaf81b #find sensitive files
    - 6469befa-748a-4b9c-a96d-f191fde47d89 #create staging dir
```
