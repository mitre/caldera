import abc

from abc import ABC


class C2Passive(ABC):

    @property
    def display(self):
        return dict(name=self.name, description=self.description)

    @abc.abstractmethod
    def __init__(self, config):
        self.name = config['name']
        self.description = config['description']
        self.enabled = config['enabled']

    @abc.abstractmethod
    def valid_config(self):
        """
        Check whether the yaml file configuration is valid
        :return: True or False
        """
        return

    @abc.abstractmethod
    async def start(self):
        """
        Start the passive event loop for an additional C2 channel
        :return:
        """
        pass
