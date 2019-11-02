from app.utility.base_world import BaseWorld
from app.utility.logger import Logger


class BaseService(BaseWorld):

    _services = dict()

    def add_service(self, name, svc):
        self.__class__._services[name] = svc
        return Logger(name)

    @classmethod
    def get_service(cls, name):
        return cls._services.get(name)

    @classmethod
    def get_services(cls):
        return cls._services
