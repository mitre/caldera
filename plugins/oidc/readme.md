**MITRE Caldera Plugin: Keycloak OIDC**

OIDC is a Caldera plugin that provides OpenID authentication for Caldera by establishing Caldera as a OIDC Service Provider (SP). To use this plugin, users will need to have Caldera configured as an application in their Identity Provider (IdP), and a conf/keycloak_oidc_settings.json file will need to be created in the plugin with the appropriate OIDC settings and IdP and SP information.

When enabled and configured, this plugin will provide the following:

- When browsing to the main Caldera site (e.g. <http://localhost:8888/>) or to the /enter URL for the Caldera site (e.g. <http://localhost:8888/enter>), unauthenticated users will be redirected to their IdP login page rather than to the default Caldera login page. If the OIDC settings are not properly configured or if there is an issue with attempting the redirect, the user will be redirected to the default Caldera login page as a failsafe.
- When users access the Caldera application directly from their IdP, they will immediately authenticate into Caldera without having to provide login credentials, provided that Caldera was configured correctly within the IdP settings. If the OIDC login fails for whatever reason (e.g. the application was provisioned using a username that does not exist within Caldera), the user will be taken to the default Caldera login page.

**Setup**

There are two main setup components required for OIDC authentication within this plugin:

- The IdP administrators need to configure Caldera as an application within the IdP platform
- Caldera administrators need to configure the conf/ keycloak_oidc_settings.json settings file within the OIDC plugin.

**Installing Dependencies**

To install dependencies, run the following from within the plugin directory::

- pip3 install -r requirements.txt

**Configuring Caldera Within the IdP Platform**

To provision Caldera access for users within the Identity Provider, follow the instructions for your particular Identity Provider to create the Caldera application with the appropriate OIDC settings.

- When asked for the " redirect_uri " use the HTTP endpoint for your Caldera server without the trailing slash (e.g. <http://localhost:8888/oidc>)
- Give the realm name , clientID and client secret

**Configuring OIDC settings within Caldera**

- Once Caldera is configured as an application within your IdP, you can start creating the conf/ keycloak_oidc_settings.json file within the plugin

![image](https://github.com/Sandiptank70/caldera/assets/53286381/ee7a1320-1e6b-4315-b1cb-919658517166)


Setting the OIDC Login Handler

Once Caldera's OIDC settings are configured and Caldera is set up on the IdP platform, the final step requires setting the OIDC login handler as the main login handler in the Caldera config YAML file. Within the config file, set auth.login.handler.module to plugins.oidc.app.oidc_login_handler as shown below:

- auth.login.handler.module: plugins.oidc.app.oidc_login_handler

Restart the Caldera server, and any future authentication requests will now be handled via OIDC according to the previously established settings.
