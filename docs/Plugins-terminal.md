Plugin: terminal
=============

The terminal plugin adds shell-capability to CALDERA. 

When this plugin is loaded, you'll get access to a new GUI page which allows you to drop reverse-shells on target hosts and interact manually with the machines. When starting a session, a reverse-shell is downloaded and started on the agent, connecting back to the server over port 5678.

## Custom commands
There are a handful of custom commands built into the reverse-shell.
* **upload**: exfil a single file to the server
> example: upload notes.txt
* **download**: drop any file from any of the server's payload directories on the target
> example: download sandcat.go-linux