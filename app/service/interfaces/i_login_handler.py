import abc

from app.utility.base_object import BaseObject


class LoginHandlerInterface(abc.ABC, BaseObject):
    def __init__(self, name):
        self._name = name

    @abc.abstractmethod
    async def handle_login(self, request, **kwargs):
        """Handle login request

        :param request:
        :return: the response/location of where the user is trying to navigate
        :raises: HTTP exception, such as HTTPFound for redirect, or HTTPUnauthorized
        """
        pass

    @abc.abstractmethod
    async def handle_login_redirect(self, request, **kwargs):
        """Handle redirect to login

        :param request:
        :return: the response/location of where the user is trying to navigate
        :raises: HTTP exception, such as HTTPFound for redirect, or HTTPUnauthorized
        """
        pass

    @property
    def name(self):
        return self._name
