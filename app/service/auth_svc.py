import base64
from collections import namedtuple

from aiohttp import web
from aiohttp.web_exceptions import HTTPUnauthorized, HTTPForbidden
from aiohttp_security import SessionIdentityPolicy, check_permission, remember, forget
from aiohttp_security import setup as setup_security
from aiohttp_security.abc import AbstractAuthorizationPolicy
from aiohttp_session import setup as setup_session
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from cryptography import fernet
import ldap3

from app.service.interfaces.i_auth_svc import AuthServiceInterface
from app.utility.base_service import BaseService


def for_all_public_methods(decorator):
    """class decorator -- adds decorator to all public methods"""

    def decorate(cls):
        for attr in cls.__dict__:
            if callable(getattr(cls, attr)) and attr[0] != '_':
                setattr(cls, attr, decorator(getattr(cls, attr)))
        return cls

    return decorate


def check_authorization(func):
    """
    Authorization Decorator
    This requires that the calling class have `self.auth_svc` set to the authentication service.
    """
    async def process(func, *args, **params):
        return await func(*args, **params)

    async def helper(*args, **params):
        await args[0].auth_svc.check_permissions('app', args[1])
        result = await process(func, *args, **params)
        return result
    return helper


class AuthService(AuthServiceInterface, BaseService):

    User = namedtuple('User', ['username', 'password', 'permissions'])

    def __init__(self):
        self.user_map = dict()
        self.log = self.add_service('auth_svc', self)
        self.ldap_config = self.get_config('ldap')

    async def apply(self, app, users):
        for group, u in users.items():
            self.log.debug('Created authentication group: %s' % group)
            for k, v in u.items():
                self.user_map[k] = self.User(k, v, (group, 'app'), )
        app.user_map = self.user_map
        fernet_key = fernet.Fernet.generate_key()
        secret_key = base64.urlsafe_b64decode(fernet_key)
        storage = EncryptedCookieStorage(secret_key, cookie_name='API_SESSION')
        setup_session(app, storage)
        policy = SessionIdentityPolicy()
        setup_security(app, policy, DictionaryAuthorizationPolicy(self.user_map))

    @staticmethod
    async def logout_user(request):
        await forget(request, web.Response())
        raise web.HTTPFound('/login')

    async def login_user(self, request):
        """
        Log a user in and save the session
        :param request:
        :return: the response/location of where the user is trying to navigate
        """
        data = await request.post()
        username = data.get('username')
        password = data.get('password')
        if self.ldap_config:
            verified = await self._ldap_login(username, password)
        else:
            verified = await self._check_credentials(request.app.user_map, username, password)

        if verified:
            self.log.debug('%s logging in:' % username)
            response = web.HTTPFound('/')
            await remember(request, response, username)
            raise response
        self.log.debug('%s failed login attempt: ' % username)
        raise web.HTTPFound('/login')

    async def check_permissions(self, group, request):
        try:
            if request.headers.get('KEY') == self.get_config('api_key_red') or \
                    request.headers.get('KEY') == self.get_config('api_key_blue'):
                return True
            await check_permission(request, group)
        except (HTTPUnauthorized, HTTPForbidden):
            raise web.HTTPFound('/login')

    async def get_permissions(self, request):
        identity_policy = request.config_dict.get('aiohttp_security_identity_policy')
        identity = await identity_policy.identify(request)
        if identity in self.user_map:
            return [self.Access[p.upper()] for p in self.user_map[identity].permissions]
        elif request.headers.get('KEY') == self.get_config('api_key_red'):
            return self.Access.RED, self.Access.APP
        elif request.headers.get('KEY') == self.get_config('api_key_blue'):
            return self.Access.BLUE, self.Access.APP
        return ()

    """ PRIVATE """

    @staticmethod
    async def _check_credentials(user_map, username, password):
        user = user_map.get(username)
        if not user:
            return False
        return user.password == password

    async def _ldap_login(self, username, password):
        server = ldap3.Server(self.ldap_config.get('server'))
        dn = self.ldap_config.get('dn')
        userattr = self.ldap_config.get('userattr') or 'uid'
        userstring = '{}={},{}'.format(userattr, username, dn)
        with ldap3.Connection(server, user=userstring, password=password) as conn:
            if conn.bind():
                return True
            else:
                return False


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
