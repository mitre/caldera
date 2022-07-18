import base64
from collections import namedtuple
from hmac import compare_digest
from importlib import import_module

from aiohttp import web, web_request
from aiohttp.web_exceptions import HTTPUnauthorized, HTTPForbidden
from aiohttp_security import api as aiohttp_security_api
from aiohttp_security import SessionIdentityPolicy, check_permission, remember, forget
from aiohttp_security import setup as setup_security
from aiohttp_security.abc import AbstractAuthorizationPolicy
from aiohttp_session import setup as setup_session
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from cryptography import fernet

from app.service.interfaces.i_auth_svc import AuthServiceInterface
from app.service.interfaces.i_login_handler import LoginHandlerInterface
from app.service.login_handlers.default import DefaultLoginHandler
from app.utility.base_service import BaseService


HEADER_API_KEY = 'KEY'
COOKIE_SESSION = 'API_SESSION'
CONFIG_API_KEY_RED = 'api_key_red'
CONFIG_API_KEY_BLUE = 'api_key_blue'
CONFIG_AUTH_LOGIN_HANDLER = 'auth.login.handler.module'


def for_all_public_methods(decorator):
    """class decorator -- adds decorator to all public methods"""

    def decorate(cls):
        for attr in cls.__dict__:
            if callable(getattr(cls, attr)) and attr[0] != '_':
                setattr(cls, attr, decorator(getattr(cls, attr)))
        return cls

    return decorate


def check_authorization(func):
    """Authorization Decorator
    This requires that the calling class have `self.auth_svc` set to the authentication service.
    """
    async def process(func, *args, **params):
        return await func(*args, **params)

    async def helper(*args, **params):
        if len(args) > 1 and type(args[1]) is web_request.Request:
            await args[0].auth_svc.check_permissions('app', args[1])
        result = await process(func, *args, **params)
        return result
    return helper


class AuthService(AuthServiceInterface, BaseService):
    User = namedtuple('User', ['username', 'password', 'permissions'])

    def __init__(self):
        self.user_map = dict()
        self.log = self.add_service('auth_svc', self)
        self._login_handler = None
        self._default_login_handler = None

    @property
    def default_login_handler(self):
        return self._default_login_handler

    async def apply(self, app, users):
        if users:
            for group, user in users.items():
                self.log.debug('Created authentication group: %s', group)
                for username, password in user.items():
                    await self.create_user(username, password, group)
        app.user_map = self.user_map
        fernet_key = fernet.Fernet.generate_key()
        secret_key = base64.urlsafe_b64decode(fernet_key)
        storage = EncryptedCookieStorage(secret_key, cookie_name=COOKIE_SESSION)
        setup_session(app, storage)
        policy = SessionIdentityPolicy()
        setup_security(app, policy, DictionaryAuthorizationPolicy(self.user_map))

    async def create_user(self, username, password, group):
        self.user_map[username] = self.User(username, password, (group, 'app'), )

    @staticmethod
    async def logout_user(request):
        await forget(request, web.Response())
        raise web.HTTPFound('/')

    async def login_user(self, request):
        """Log a user in and save the session

        :param request:
        :raises web.HTTPRedirection: the HTTP response/location of where the user is trying to navigate
        :raises web.HTTPUnauthorized: HTTP unauthorized response as provided by the login handler.
        :raises web.HTTPForbidden: HTTP forbidden response as provided by the login handler.
        :raises web.HTTPSuccessful: HTTP successful response as provided by the login handler.
        """
        try:
            self.log.debug('Using login handler "%s" for login', self._login_handler.name)
            await self._login_handler.handle_login(request)
        except (web.HTTPRedirection, web.HTTPUnauthorized, web.HTTPForbidden, web.HTTPSuccessful) as allowed_exception:
            raise allowed_exception
        except Exception as e:
            self.log.exception('Exception when handling login request.')

            # Fallback if not already using default login handler
            if not isinstance(self._login_handler, DefaultLoginHandler):
                self.log.debug('Falling back to default login handler')
                return await self._default_login_handler.handle_login(request)
            else:
                # We ran into an unexpected exception when using the default login handler.
                raise e

    async def login_redirect(self, request, use_template=True):
        """Redirect user to login page using the configured login handler. Will fall back to the
        default login handler if an unexpected exception is raised.

        :param request:
        :param use_template: Determines if the login handler should return an html template rather than raise
            an HTTP redirect, if applicable. Defaults to True.
        :type use_template: bool, optional
        """
        try:
            self.log.debug('Using login handler "%s" for login redirect', self._login_handler.name)
            return await self._login_handler.handle_login_redirect(request, use_template=use_template)
        except (web.HTTPRedirection, web.HTTPUnauthorized, web.HTTPForbidden, web.HTTPSuccessful) as allowed_exception:
            raise allowed_exception
        except Exception as e:
            self.log.exception('Exception when handling login redirect.')

            # Fallback if not already using default login handler
            if not isinstance(self._login_handler, DefaultLoginHandler):
                self.log.debug('Falling back to default login handler')
                return await self._default_login_handler.handle_login_redirect(request, use_template=use_template)
            else:
                # We ran into an unexpected exception when using the default login handler.
                raise e

    def request_has_valid_api_key(self, request):
        request_api_key = request.headers.get(HEADER_API_KEY)
        if request_api_key is None:
            return False
        for i in [CONFIG_API_KEY_RED, CONFIG_API_KEY_BLUE]:
            api_key = self.get_config(i)
            if api_key is not None and compare_digest(request_api_key, api_key):
                return True
        return False

    async def request_has_valid_user_session(self, request):
        return await aiohttp_security_api.authorized_userid(request) is not None

    async def handle_successful_login(self, request, username):
        self.log.debug('%s logging in', username)
        response = web.HTTPFound('/')
        await remember(request, response, username)
        raise response

    async def check_permissions(self, group, request):
        try:
            if self.request_has_valid_api_key(request):
                return True
            await check_permission(request, group)
        except (HTTPUnauthorized, HTTPForbidden):
            return await self.login_redirect(request, use_template=False)

    async def get_permissions(self, request):
        identity_policy = request.config_dict.get('aiohttp_security_identity_policy')
        identity = await identity_policy.identify(request)
        if identity in self.user_map:
            return [self.Access[p.upper()] for p in self.user_map[identity].permissions]
        elif request.headers.get(HEADER_API_KEY) == self.get_config(CONFIG_API_KEY_RED):
            return self.Access.RED, self.Access.APP
        elif request.headers.get(HEADER_API_KEY) == self.get_config(CONFIG_API_KEY_BLUE):
            return self.Access.BLUE, self.Access.APP
        return ()

    async def is_request_authenticated(self, request):
        if self.request_has_valid_api_key(request):
            return True
        return await self.request_has_valid_user_session(request)

    async def set_login_handlers(self, services, primary_handler=None):
        """Sets the default login handler for the auth service, as well as the custom login handler if specified in the
        primary_handler parameter or in the config file. The custom login handler will take priority for login methods
        during login_user and redirects during check_permissions.

        If no login handler was specified in the config file or via the primary_handler parameter,
        the auth service will use only the default handler.

        :param services: services used to set up the login handlers.
        :type services: dict
        :param primary_handler: Login handler for the auth service. If None, the config file will
            be used to load the primary login handler. Must implement the LoginHandlerInterface.
            Defaults to None.
        :type primary_handler: LoginHandlerInterface, optional
        :raises TypeError: The provided login handler does not implement the LoginHandlerInterface.
        """
        self._configure_default_login_handler(services)
        provided_handler = primary_handler if primary_handler else self._get_login_handler_from_config(services)
        if provided_handler:
            if isinstance(provided_handler, LoginHandlerInterface):
                self.log.debug('Setting primary login handler: %s', provided_handler.name)
                self._login_handler = provided_handler
            else:
                raise TypeError('Attempted to set login handler that does not implement LoginHandlerInterface.')
        else:
            self.log.debug('Using default login handler.')
            self._login_handler = self._default_login_handler

    def _get_login_handler_from_config(self, services):
        login_handler_module_path = self.get_config(CONFIG_AUTH_LOGIN_HANDLER)
        if login_handler_module_path and login_handler_module_path != 'default':
            self.log.debug('Fetching login handler from config from module: %s', login_handler_module_path)
            login_handler = import_module(login_handler_module_path).load_login_handler(services)
            return login_handler

    def _configure_default_login_handler(self, services):
        self._default_login_handler = DefaultLoginHandler(services)


class DictionaryAuthorizationPolicy(AbstractAuthorizationPolicy):

    def __init__(self, user_map):
        super().__init__()
        self.user_map = user_map

    async def authorized_userid(self, identity):
        """Retrieve authorized user id.
        Return the user_id of the user identified by the identity
        or 'None' if no user exists related to the identity.
        """
        if identity in self.user_map:
            return identity

    async def permits(self, identity, permission, context=None):
        """Check user permissions.
        Return True if the identity is allowed the permission in the
        current context, else return False.
        """
        user = self.user_map.get(identity)
        if not user:
            return False
        return permission in user.permissions
