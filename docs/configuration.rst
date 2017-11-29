=============
Configuration
=============

Caldera Server Configuration
============================

The server configuration is located in `caldera/caldera/conf/settings.yaml`. It will be created after the Caldera server is run
once.

Configurable options include:
 - the IP and port that the server will bind to
 - the SSL certificate and key that the server will use
 - the default username and password which is used to login to the web admin panel
 - the SSL certificate and proxy needed to communicate with external sites

The server uses an SSL certificate and private key. Instructions to generate an SSL certificate and key are printed
to the console if no SSL certificate is detected.
The certificate and key location is configured within the settings.yaml file by editing the `crypto:cert` and
`crypto:key` variables.

The default username and password is stored in the configuration file. If this value is modified,
it does not affect existing user accounts, which will still remain and must be manually modified through the Settings
interface within the Administration Panel.

The proxy settings for the server can be found in the settings.yaml, under the `proxy:default:http` and
`proxy:default:https` variables. If a CA ssl certificate is necessary, reference its location in the
`proxy:default:cert` variable. In the event that a site Caldera reaches out to requires a unique cert or proxy, simply
duplicate a set of variables under proxy, replacing default with the site's base, and configure the variables
appropriately.

Caldera Agent Configuration
===========================

Customizing the conf.yml
------------------------

Settings for cagent are stored in a file `conf.yml`. The **CALDERA** server generates a conf.yml file that is generally
correct, however it may have to be modified if the caldera server cannot detect certain settings.

`url_root`
    The `url_root` field in `conf.yml` is the hostname of the caldera server that the agent will connect to.

`cert`
    The `cert` field should match the public certificate that the caldera server is configured to use, which by
    default is located at `caldera/caldera/conf/cert.pem`. Note that because the certificate is a multiline string,
    there is a hanging indent in the example configuration file

`verify_hostname`
    The `verify_hostname` flag can be set to true. This will cause the Agent to verify that the hostname on the Server's
    certificate matches the hostname of the Server that it is connecting to. If you are not sure whether the
    certificate contains the appropriate hostname or you encounter problems connecting to the Server, you may
    set this to false.

`logging_level`
    The `logging_level` field can be set to various levels of verbosity:

    - `info`
    - `debug`
    - `warning`
    - `error`

    The default logging_level of `warning` is generally appropriate. Cagent logs are stored in the Windows Event Log
    and can be accessed using the Windows Event Viewer. Logs in the Event Viewer are stored under
    `Windows Logs>Application`.

Cagent Debug Modes
------------------

Normally cagent is installed and run as a service, however it can be run for debugging
purposes without actually making it a service. This will also print out error messages to the console
instead of the Windows Event Log: ::

    cagent.exe debug

For running CALDERA *operations*, cagent should be installed as a service or executed in
an elevated command prompt on each computer taking part in the adversary emulation exercise.
