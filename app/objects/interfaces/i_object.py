import abc


class FirstClassObjectInterface(abc.ABC):

    @property
    @abc.abstractmethod
    def unique(self):
        raise NotImplementedError

    @abc.abstractmethod
    def store(self, ram):
        raise NotImplementedError
