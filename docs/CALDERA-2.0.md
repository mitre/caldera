CALDERA 2.0
==========

In April 2019, the CALDERA team pushed out several large changes to the core CALDERA code-base, effectively creating a "new" version of CALDERA: CALDERA 2.0. This new version of CALDERA featured a much more modular plugin-based architecture, many bug-fixes, a new GUI, and most importantly, the introduction of two operating modes: **adversary mode** and **chain mode**. 

### Adversary Mode
Adversary mode is the classic CALDERA capability. Functionally, the mode is the same as it was when first released in 2017 -- it still runs fully automated, end-to-end operations using a dynamic planner -- although now it has some internal optimizations, bug fixes, and a different GUI. Setup and requirements for this mode are also largely the same as when first released: you must install the CAgent software on each endpoint you want to test (Windows only), pointing the agent back to the CALDERA server to run the operation. Installing the agent is now much simpler, and can be done via a PowerShell script that's displayed on the adversary mode page. From an architecture perspective, the adversary mode functionality is now entirely encapsulated in the "adversary" plugin; without loading this plugin, the functionality will be absent.

### Chain Mode
Chain mode is the new operating mode for CALDERA, and was first introduced in the "2.0" release in mid 2019. This mode was designed to allow users to orchestrate/string together atomic unit tests into larger attack sequences; unlike adversary mode, chain mode was originally not designed to be dynamic, and each operation was to be run explicitly sans any variables in commands. Chain mode's relatively simple use case enabled us to design it with a much smaller footprint, requiring only simple agents to execute commands as dictated by the CALDERA server; unlike adversary mode, chain mode leverages a single agent (not an agent + a RAT), and only needs a single agent to be connected to the CALDERA server to test a network (as opposed to each endpoint needing to have CAgent installed). Generally speaking, chain mode has significantly less overhead than adversary mode, albeit at the cost of some of adversary mode's dynamism.

### What's the long-term plan?
Long term, we hope to subsume adversary mode's capabilities into chain mode by adding dynamism to chain mode operations, encoding input and output for each chain mode action in a way that's similar to (though more intuitive than) the way actions are encoded in adversary mode.

### Why?
After releasing the first version of chain mode, we realized that this new functionality was significantly easier to stand up than our initial adversary mode release; we've found that many people struggling to run adversary mode operations are typically struggling with that mode's dependencies/encoding. Moreover, chain mode's light overhead makes it easier to extend with new actions, allowing us to more readily encode more of the ATT&CK matrix than we could with adversary mode. We believe that shifting our operations to something lighter-weight will allow more people to use CALDERA for more use cases.

### Gotchas
Our CALDERA 2.0 push came without much fanfare -- or documentation! We've discovered that there are some minor pain points when first using this new version:

* Adversary mode is disabled by default. To use adversary mode, download the adversary mode plugin and make the appropriate changes to the main CALDERA local.conf file.
* Existing documentation on CALDERA is largely out to date. In particular, our page on readthedocs needs to be updated. Much of that information still pertains to adversary mode, although stuff that talks more broadly about CALDERA is somewhat dated.
* CALDERA's GUI is now significantly different; don't worry if it doesn't look the way it does in other public material!
* Adversary mode still only supports execution on Windows machines. Chain mode by contrast has support for Windows, Linux, or Mac.
