Plugin: SSL
=========

The SSL plugin adds HTTPS to CALDERA. 
> This plugin only works if CALDERA is running on a Linux or MacOS machine. It requires HaProxy (>= 1.8) to be installed prior to using it.

When this plugin has been loaded, CALDERA will start the HAProxy service on the machine and then serve CALDERA at hxxps://[YOUR_IP]:443, instead of the normal hxxp://[YOUR_IP]:8888.

CALDERA will **only** be available at https://[YOUR_IP]:443 when using this plugin. All deployed agents should use the correct address to connect to CALDERA. 
