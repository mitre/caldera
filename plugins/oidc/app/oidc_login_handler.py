import logging
from aiohttp import web

from app.service.interfaces.i_login_handler import LoginHandlerInterface

HANDLER_NAME = 'OIDC Login Handler'


def load_login_handler(services):
    return OidcLoginHandler(services)


class OidcLoginHandler(LoginHandlerInterface):
    def __init__(self, services):
        super().__init__(services, HANDLER_NAME)
        self.services = services
        self.log = logging.getLogger('oidc_login_handler')

    async def handle_login(self, request, **kwargs):
        """Redirects login request to OIDC login page. If username/password were included in the request, then
        the default login handler mechanism will be used.
        """
        # Only handle login if username and password are not included in the request. If username and password
        # are included, then this is a standard login request and should not redirect to OIDC.
        data = await request.post()
        if 'username' not in data and 'password' not in data:
            self.log.debug('Handling oidc login')
            await self.handle_login_redirect(request)
        else:
            auth_svc = self.services.get('auth_svc', None)
            if not auth_svc:
                raise Exception('Auth service not found.')
            self.log.debug('Requester provided login credentials. Using default login handler instead.')
            return await auth_svc.default_login_handler.handle_login(request, kwargs=kwargs)

    async def handle_login_redirect(self, request, **kwargs):
        """Will raise web.HTTPFound for identity provider redirect on success."""
        oidc_svc = self.services.get('oidc_svc', None)
        if not oidc_svc:
            raise Exception('OIDC service not found.')
        auth = await oidc_svc.get_oidc_auth(request)
        
        raise web.HTTPFound(auth)
