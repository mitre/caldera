What is a planner?
===============

A planner is a module within CALDERA which contains logic for how a running [operation](What-is-an-operation.md) should make decisions about which abilities to use and in what order.

Specifically, a planner's logic contains the decision making to execute a single phase of an operation. The core service - operation_svc.py - calls the planner for each phase of an adversary during an operation. 

> Planners are single module Python files. Planners utilize the core system's planning_svc.py, which has planning logic useful for various types of planners.

## The _Sequential_ planner

CALDERA ships with a default planner, sequential. During each phase of the operation, the sequential planner loops through all agents (which are part of the operation's group) and sends each of them a list of all ability commands the planner thinks it can complete. This decision is based on the agent matching the operating system (execution platform) of the ability and the ability command having no unsatisfied variables. It then waits for each agent to complete their list of commands before moving on to the next phase.