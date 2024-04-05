import json
import os
import warnings
warnings.filterwarnings('ignore', 'defusedxml.lxml is no longer supported and will be removed in a future release.', DeprecationWarning)
import requests
from aiohttp import web
from pathlib import Path
from keycloak import KeycloakOpenID
from aiohttp import web
from app.utility.base_service import BaseService




class OidcService(BaseService):
    def __init__(self):
        self.config_dir_path = os.path.join(Path(__file__).parents[1], 'conf')
        self.settings_path = os.path.join(self.config_dir_path, 'keycloak_oidc_settings.json')
        with open(self.settings_path, 'rb') as settings_file:
            self._oidc_config = json.load(settings_file)
        self.client_id = self._oidc_config['client_id']
        self.client_secret = self._oidc_config['client_secret']
        self.redirect_uri = self._oidc_config['redirect_uri']
        self.server_url = self._oidc_config['server_url']
        self.realm_name = self._oidc_config['realm_name']

        self.keycloakOpenID = KeycloakOpenID(server_url=self.server_url,
                                             client_id=self.client_id,
                                             realm_name=self.realm_name,
                                             client_secret_key=self.client_secret)

        self.log = self.add_service('oidc_svc', self)

    async def oidc(self, request):
        """Handle OIDC authentication."""
        try:
            await self._oidc_login(request)
        except web.HTTPRedirection as http_redirect:
            raise http_redirect
        except Exception as e:
            self.log.exception('Exception when handling /oidc request: %s', e)
        self.log.debug('Redirecting to main login page')
        raise web.HTTPFound('/login')

    async def set_oidc_login_handler(self):
        """Set self as the optional login handler for the auth service."""
        self.log.debug('Setting oidc as primary login handler for auth service.')
        auth_svc = self.get_service('auth_svc')
        if not auth_svc:
            raise Exception('Auth service not available')
        await auth_svc.set_optional_login_handler(self)

    async def get_oidc_auth(self, request):
        url = self.keycloakOpenID.auth_url(redirect_uri=f"{self.redirect_uri}/oidc",scope="email")
        return url

    async def _oidc_login(self, request):
        self.log.debug('Handling login from OIDC identity provider.')
        method = request.method
        path = request.path
        query_parameters = request.query
        code = query_parameters.get('code')
        code=self.keycloakOpenID.token(code=code,grant_type="authorization_code",redirect_uri=f"{self.redirect_uri}/oidc")
        userinfo=self.keycloakOpenID._token_info(code['access_token'],"introspect")
        username =  userinfo['username']
        await self._handle_app_authentication(request, username)

    async def _handle_app_authentication(self, request, username):
        
        await self._validate_username(request, username)
        
        

    async def _validate_username(self, request, app_username):
        auth_svc = self.get_service('auth_svc')
        if not auth_svc:
            raise Exception('Auth service not available')
        if app_username in auth_svc.user_map:
           
            self.log.info('User  authenticated via OIDC under application user "%s"',
                           app_username)
            await auth_svc.handle_successful_login(request, app_username)
        else:
            self.log.warn('Application username "%s" not configured for login', app_username)
            self.log.info('User  failed to authenticate via OIDC under application user "%s"',
                           app_username)
    
