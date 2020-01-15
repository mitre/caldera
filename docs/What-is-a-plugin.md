What is a plugin?
==============

CALDERA is built using a plugin architecture on top of the core system. Plugins are separate git repositories that plug new features into the core system. Each plugin resides in the plugins directory and is loaded into CALDERA by adding it to the [local.yml file](Customizing-CALDERA-configuration.md).

Each plugin contains a single hook.py file in its root directory. This file should contain an initialize function, which gets called automatically for each loaded plugin when CALDERA boots. The initialize function contains the plugin logic that is getting "plugged into" the core system. This function takes two parameters:

1. **app**: the aiohttp application object, which allows the plugin to manipulate any of the web server/API components
2. **services**: a list of core services that live inside the core system. 

A plugin can add nearly any new functionality/features to CALDERA by using the two objects above. 

[Interested in building a plugin?](How-to-Build-Plugins.md)
