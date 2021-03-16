import abc


class LoginHandlerInterface(abc.ABC):
    @abc.abstractmethod
    async def handle_login(self, request):
        """
        Handle login request
        :param request:
        :return: the response/location of where the user is trying to navigate
        """
        pass

    @abc.abstractmethod
    async def handle_login_redirect(self, request):
        """
        Handle redirect to login
        :param request:
        :return: the response/location of where the user is trying to navigate
        """
        pass
