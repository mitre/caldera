import abc
from app.utility.base_object import BaseObject


class LoginHandlerInterface(abc.ABC, BaseObject):
    _name = 'Login Handler Interface'

    @abc.abstractmethod
    async def handle_login(self, request, **kwargs):
        """
        Handle login request
        :param request:
        :return: the response/location of where the user is trying to navigate
        """
        pass

    @abc.abstractmethod
    async def handle_login_redirect(self, request, **kwargs):
        """
        Handle redirect to login
        :param request:
        :return: the response/location of where the user is trying to navigate
        """
        pass

    @property
    def name(self):
        return self._name
