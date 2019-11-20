import abc
from abc import ABC


class C2Passive(ABC):

    @abc.abstractmethod
    def start(self, app):
        """
        Starts this C2 channel
        :param app: asyncio app object
        :return:
        """
        return
