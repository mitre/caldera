========
Overview
========

**CALDERA** is a tool that can perform automated adversarial assessments against Windows enterprise networks,
requiring zero prior knowledge about the environment to run. **CALDERA** works by leveraging its built in semantic model
for how Windows enterprise domains are structured, an adversary model describing an attacker's goals and actions, and
an artificially intelligent planner that makes decisions about which actions to perform. **CALDERA** does this all by
performing real actions on systems similar to how an adversary would so that the same kinds of data gets generated:
**CALDERA** features a remote access tool (RAT) that performs adversary actions on infected hosts and copies itself over
the network to increase its foothold. To most realistically emulate an adversary, **CALDERA**'s model uses common Windows
domain elements -- users, shares, credentials -- and features a library of executable techniques curated from ATT&CK,
including favorites such as running Mimikatz to dump credentials and remote execution with WMI.

As a fully automated tool, defenders can use **CALDERA** to verify their defenses are working appropriately and as a
resource to test defensive tools and analytics. Additionally, **CALDERA**'s modular design allows users to customize
each individual operation and provides a flexible logic so that users can incorporate their own techniques into
**CALDERA**'s automated assessments.