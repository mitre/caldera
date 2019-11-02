from enum import Enum

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

    class LinkState(Enum):
        EXECUTE = -3
        DISCARD = -2
        PAUSE = -1

    class Reason(Enum):
        PLATFORM = 0
        EXECUTOR = 1
        FACT_DEPENDENCY = 2
        OP_RUNNING = 3
        UNTRUSTED = 4


