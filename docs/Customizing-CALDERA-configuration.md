Customizing CALDERA's configuration
============================

Caldera's configuration file is located in the `conf/` directory. By default, CALDERA will use the `default.yml` file that is included with CALDERA, but this can be overridden by taking by creating your own `local.yml` file and saving it in the `conf/` directory. The name of the config file to use can also be specified with the `-E` flag when starting the server.

Caldera will choose the configuration file to use in the following order:

1. A config specified with the `-E` or `--environment` command-line options.  For instance, if started with `python caldera.py -E foo`, CALDERA will load it's configuration from `conf/foo.yml`.
2. `conf/local.yml`: Caldera will prefer the local configuration file if no other options are specified.
3. `conf/default.yml`: If no config is specified with the `-E` option and it cannot find a `conf/local.yml` configuration file, CALDERA will use its default configuration options.

The YAML configuration file contains all the configuration CALDERA requires to boot up. An example configuration file is below:

```yaml
host: 127.0.0.1
port: 8888
exfil_dir: /tmp
enabled_plugins:
  - stockpile
  - sandcat
api_key: ADMIN123
users:
  admin: admin
```

A few key things to note:

* **Host**: the IP address CALDERA is available at. You may need to change this to 0.0.0.0 to serve CALDERA on all interfaces, if you anticipate remote machines directly connecting to it.
* **Port**: the port you serve CALDERA on
* **Exfil_dir**: the directory to use when an ability exfiltrates files from the agent, sending them back to CALDERA. Any file(s) posted to the /file/upload endpoint will end up in this directory.
* **Enabled_plugins**: the list of all loaded [plugins](What-is-a-plugin.md). A plugin must be in this list to be available when CALDERA is running. Adding a plugin to this list will result in that plugin's hook.py file getting called when CALDERA boots up.
* **API_KEY**: A password to use when accessing CALDERA programmatically.
* **Users**: the username/password credentials of all accounts you want to access the CALDERA login page
