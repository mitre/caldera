import abc


class AuthServiceInterface(abc.ABC):

    @abc.abstractmethod
    def apply(self, app, users):
        """
        Set up security on server boot
        :param app:
        :param users:
        :return: None
        """
        pass

    @staticmethod
    @abc.abstractmethod
    def logout_user(request):
        """
        Log the user out
        :param request:
        :return: None
        """
        pass

    @abc.abstractmethod
    def login_user(self, request):
        """
        Kick off all scheduled jobs, as their schedule determines
        :return:
        """
        pass

    @abc.abstractmethod
    def check_permissions(self, group, request):
        """
        Check if a request is allowed based on the user permissions
        :param group:
        :param request:
        :return: None
        """
        pass

    @abc.abstractmethod
    def get_permissions(self, request):
        pass
