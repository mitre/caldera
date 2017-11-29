# Virtual Red Team System

## ExtroViRTS
This component parallels an operator that grows in knowledge of a
network and makes higher level decisions regarding mission requirements, and
techniques to use. As a decision making engine, this component intentionally
is not concerned with intricacies of performing a technique, and instead
focuses on mission requirements and restrictions.

## REST API


#### Network
- [/api/networks](#apinetworks)
- [/api/networks/(network_id)](#apinetworksnetwork_id)
- [/api/networks/(network_id)/hosts](#apinetworksnetwork_idhosts)
- [/api/networks/(network_id)/hosts/(host_id)](#apinetworksnetwork_idhostshost_id)
- [/api/networks/(network_id)/hosts/(host_id)/commands](#apinetworksnetwork_idhostshost_idcommands)
- [/api/networks/(network_id)/hosts/(host_id)/commands/(command_id)](#apinetworksnetwork_idhostshost_idcommandscommand_id)
- [/api/networks/(network_id)/hosts/(host_id)/rats](#apinetworksnetwork_idhostshost_idrats)
- [/api/networks/(network_id)/hosts/(host_id)/rats/(rat)](#apinetworksnetwork_idhostshost_idratsrat_id)
- [/api/networks/(network_id)/hosts/(host_id)/rats/(rat)/ivcommands](#apinetworksnetwork_idhostshost_idratsrat_idivcommands)
- [/api/networks/(network_id)/hosts/(host_id)/rats/(rat)/ivcommands/(ivcommand)](#apinetworksnetwork_idhostshost_idratsrat_idivcommandsivcommand_id)

#### Operations
- [/api/operations](#apioperations)
- [/api/operations/(operation_id)](#apioperationsoperation_id)
- [/api/operations/(operation_id)/networks](#apioperationsoperation_idnetworks)
- [/api/operations/(operation_id)/networks/(network_id)](#apioperationsoperation_idnetworksnetwork_id)
- [/api/operations/(operation_id)/actions](#apioperationsoperation_idactionsaction_id)
- [/api/operations/(operation_id)/actions/(action_id)](#apioperationsoperation_idactionsaction_id)

#### Adversary Profile
- [/api/profiles](#apiprofiles)
- [/api/profiles/(profile_id)](#apiprofilesprofile_id)
- [/api/profiles/(profile_id)/techniques](#apiprofilesprofile_idtechniques)
- [/api/profiles/(profile_id)/techniques/(technique_id)](#apiprofilesprofile_idtechniquestechnique_id)

#### Techniques
- [/api/techniques](#apitechniques)
- [/api/techniques/(technique)](#apitechniquestechnique_id)

#### Jobs
- [/api/jobs](#apijobs)
- [/api/jobs/(job_id)](#apijobsjob_id)



## API Reference

####  `/api/jobs`
Retrieves or changes list of jobs visible by the active token.
*Methods*: 'GET', 'POST'


-----
#### `/api/jobs/(job_id)`
Retrieves or updates a job.
*Methods*: 'GET', 'PUT', 'DELETE'


-----
#### `/api/networks`
Enumerate or add the active networks
*Methods*: 'GET', 'POST'


-----
#### `/api/networks/(network_id)`
Individual network.
*Supports*: 'GET', 'PUT', 'DELETE'


-----
#### `/api/networks/(network_id)/hosts`
Enumerate or add to the active hosts on a network.
*Supports*: 'GET', 'POST'


-----
#### `/api/networks/(network_id)/hosts/(host_id)`
View or update an active host on a network
*Supports*: 'GET', 'PUT', 'DELETE'

-----
#### `/api/networks/(network_id)/hosts/(host_id)/commands`
Enumerate or add a command to a host
*Supports*: 'GET', 'POST'

-----
#### `/api/networks/(network_id)/hosts/(host_id)/commands/(command_id)`
View or update a command to a host agent
*Supports*: 'GET', 'PUT', 'DELETE'

-----
#### `/api/networks/(network_id)/hosts/(host_id)/rats`
Enumerate or add a an rat instance on a host
*Supports*: 'GET', 'POST'

-----
#### `/api/networks/(network_id)/hosts/(host_id)/rats/(rat)`
View or update an rat
*Supports*: 'GET', 'PUT', 'DELETE'

-----
#### `/api/networks/(network_id)/hosts/(host_id)/rats/(rat)/ivcommands`
Enumerate or add a command for rats
*Supports*: 'GET', 'POST'

-----
#### `/api/networks/(network_id)/hosts/(host_id)/rats/(rat)/ivcommands/(ivcommand)`
View or update an rat command
*Supports*: 'GET', 'PUT', 'DELETE'

-----
#### `/api/operations`
Enumerate or add to the active operations in ViRTS
*Supports*: 'GET', 'POST'


-----
#### `/api/operations/(operation_id)`
View or update an active operation
*Supports*: 'GET', 'PUT', 'DELETE'


-----
#### `/api/operations/(operation_id)/actions`
Enumerate or add to the active hosts on a network.
*Supports*: 'GET', 'POST'


-----
#### `/api/operations/(operation_id)/networks/(network_id)`
View or update an active host on a network
*Supports*: 'GET', 'PUT', 'DELETE'


-----
#### `/api/operations/(operation_id)/networks/(network_id)`
Enumerate or add to the active hosts on a network.
*Supports*: 'GET', 'POST'


-----
#### `/api/operations/(operation_id)/actions/(action_id)`
View or update an active host on a network
*Supports*: 'GET', 'PUT', 'DELETE'


-----
#### `/api/techniques`
Enumerate or add to the active techniques in ViRTS
*Supports*: 'GET', 'POST'


-----
#### `/api/techniques/(technique_id)`
View or update an active operation
*Supports*: 'GET', 'PUT', 'DELETE'