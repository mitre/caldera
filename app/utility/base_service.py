from app.utility.base_world import BaseWorld


class BaseService(BaseWorld):

    _services = dict()

    def add_service(self, name, svc):
        self.__class__._services[name] = svc
        return self.create_logger(name)

    @classmethod
    def remove_service(cls, name):
        del cls._services[name]

    @classmethod
    def get_service(cls, name):
        return cls._services.get(name)

    @classmethod
    def get_services(cls):
        return cls._services
