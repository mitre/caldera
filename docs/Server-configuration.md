Server configuration
============================

Caldera's configuration file is located at `conf/default.yml`.

## The existing default.yml

The YAML configuration file contains all the configuration CALDERA requires to boot up. An example configuration file is below:

```yaml
port: 8888
plugins:
  - sandcat
  - stockpile
  - compass
  - terminal
  - response
users:
  red:
    admin: admin
    red: admin
  blue:
    blue: admin
api_key: ADMIN123
exfil_dir: /tmp
reports_dir: /tmp
crypt_salt: REPLACE_WITH_RANDOM_VALUE
app.contact.http: http://0.0.0.0:8888
app.contact.tcp: 0.0.0.0:7010
app.contact.udp: 0.0.0.0:7011
app.contact.websocket: 0.0.0.0:7012
```

A few key things to note:

* **Port**: the port you serve CALDERA on
* **Plugins**: the list of all loaded [plugins](What-is-a-plugin.md). A plugin must be in this list to be available when CALDERA is running. Adding a plugin to this list will result in that plugin's hook.py file getting called when CALDERA boots up.
* **Users**: the username/password credentials of all accounts you want to access the CALDERA login page. Users can either be in the red or blue group.
* **API_KEY**: a password to use when accessing CALDERA programmatically.
* **Exfil_dir**: the directory to use when an ability exfiltrates files from the agent, sending them back to CALDERA. Any file(s) posted to the /file/upload endpoint will end up in this directory.
* **Reports_dir**: the directory to save all reports when the server shuts down
* **app.contact.http**: the http location you want HTTP agents (like Sandcat) to connect to.
* **app.contact.tcp**: the TCP socket you want reverse-shell agents (like Manx) to connect to.
* **app.contact.udp**: the UDP socket you want UDP agents (like Manx) to connect to
* **app.contact.websocket**: the websocket port agents can connect to


## Adding your own config file

By default, CALDERA will use the `default.yml` file that is included with CALDERA, but this can be overridden by 
taking by creating your own `local.yml` file and saving it in the `conf/` directory. 
The name of the config file to use can also be specified with the `-E` flag when starting the server.

Caldera will choose the configuration file to use in the following order:

1. A config specified with the `-E` or `--environment` command-line options.  For instance, if started with `python caldera.py -E foo`, CALDERA will load it's configuration from `conf/foo.yml`.
2. `conf/local.yml`: Caldera will prefer the local configuration file if no other options are specified.
3. `conf/default.yml`: If no config is specified with the `-E` option and it cannot find a `conf/local.yml` configuration file, CALDERA will use its default configuration options.
