What is an adversary?
=================

An adversary is a collection of abilities.

The abilities inside an adversary can optionally be grouped into phases, which allows a user to choose which order they are executed. During an operation, each phase of the adversary is run in order. If there are multiple abilities in the same phase, CALDERA will determine which order to run them, based on the information it has gathered thus far in the operation. This decision making process is known as [the planner](What-is-a-planner.md). The main reason to group abilities into phases is if an ability from a latter phase depends on the fact output from a previous phase.

An adversary can contain abilities which can be used on any platform (operating system). As an operation runs an adversary, CALDERA will match each ability to each agent and only send the matching ones to the agent.

Adversaries can be built either through the GUI or by adding YML files into `data/adversaries/` which is in the Stockpile plugin.

An adversary YML file can include a `phases` section that lists the IDs of the abilities to execute in each phase. Here is an example of such an adversary:
```
id: 5d3e170e-f1b8-49f9-9ee1-c51605552a08
name: Collection
description: A collection adversary pack
phases:
  1:
    - 1f7ff232-ebf8-42bf-a3c4-657855794cfe #find company emails
    - d69e8660-62c9-431e-87eb-8cf6bd4e35cf #find ip addresses
    - 90c2efaa-8205-480d-8bb6-61d90dbaf81b #find sensitive files
    - 6469befa-748a-4b9c-a96d-f191fde47d89 #create staging dir
```

An adversary can be included in another adversary as a pack of abilities. This can be used to organize ability phases into groups for reuse by multiple adversaries. To do so, put the ID of another adversary in a phase just like an ability. In this case, CALDERA will expand and complete all the phases of that adversary before moving to the next phase.

An adversary YML file can also contain a `packs` section that contains the IDs of other adversaries. The ability phases from these adversary packs will be merged together into any existing phases, whether from the `phases` section itself or from other adversaries in the `packs` section. Here is an example using packs without phases:
```
id: de07f52d-9928-4071-9142-cb1d3bd851e8
name: Hunter
description: Discover host details and steal sensitive files
packs:
  - 0f4c3c67-845e-49a0-927e-90ed33c044e0
  - 1a98b8e6-18ce-4617-8cc5-e65a1a9d490e
```

Adversary YML files must contain either `packs` or `phases`, or both.
