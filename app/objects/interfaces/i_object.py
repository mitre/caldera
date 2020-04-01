import abc


class FirstClassObjectInterface(abc.ABC):

    @property
    @abc.abstractmethod
    def unique(self):
        pass

    @abc.abstractmethod
    def store(self, ram):
        pass
