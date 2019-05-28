from datetime import datetime
from app.utility.authorize import Authorize
from app.utility.auth_jwt import authenticated_login, login_session, logout_session, reset_password
from functools import wraps


class AuthService:

    def __init__(self, data_svc, ssl_cert):
        self.data_svc = data_svc
        self.ssl_cert = ssl_cert
        self.auth_funcs = dict(auth = authenticated_login, login = login_session, logout = logout_session, reset = reset_password)
        self.redirect_landing = '/enter'  # set to default address to prevent redirection errors that occur if invalid

    def set_app(self, app):
        self.app_handle = app

    def set_new_auth(self, auth_handler, login_handler, logout_handler, reset_handler):
        self.auth_funcs['auth'] = auth_handler
        self.auth_funcs['login'] = login_handler
        self.auth_funcs['logout'] = logout_handler
        self.auth_funcs['reset'] = reset_handler

    def set_new_login_landing(self, landing):
        self.redirect_landing = landing

    async def login_wrapper(self, session, user):
        await self.auth_funcs['login'](self, session, user)

    async def logout_wrapper(self, session):
        await self.auth_funcs['logout'](self, session)

    async def reset_wrapper(self, submission, session):
        return await self.auth_funcs['reset'](self, submission, session)

    @staticmethod
    async def generate(password):
        return await Authorize().registration_salt_key(password)

    async def register(self, username, password):
        salt, key = await self.generate(password)
        await self.data_svc.dao.create('users', dict(username=username, password=key, salt=salt, last_login=datetime.now()))

    async def login(self, username, password):
        if not username:
            return False
        user = await self.data_svc.dao.get('users', dict(username=username))
        if not user or not await Authorize().verify(password.encode(), user[0]['password'], user[0]['salt']):
            return False
        await self.data_svc.dao.update('users', key='username', value=username, data=dict(last_login=datetime.now()))
        return True

    def set_unauthorized_route(self, allowed_requests, endpoint, target_function):
        if isinstance(allowed_requests, list):
            for ar in allowed_requests:
                self.app_handle.router.add_route(ar, endpoint, target_function)
        else:
            self.app_handle.router.add_route(allowed_requests, endpoint, target_function)

    def set_unauthorized_static(self, endpoint, target, append_version=True):
        self.app_handle.router.add_static(endpoint, target, append_version=append_version)

    def set_authorized_route(self, allowed_requests, endpoint, target_function):
        @wraps(target_function)
        async def wrapped_function(*args, **kwargs):
            core = await self.auth_funcs['auth'](self, *args, **kwargs)
            if not core:
                return await target_function(*args, **kwargs)
            else:
                return core

        if isinstance(allowed_requests, list):
            for ar in allowed_requests:
                self.app_handle.router.add_route(ar, endpoint, wrapped_function)
        else:
            self.app_handle.router.add_route(allowed_requests, endpoint, wrapped_function)
