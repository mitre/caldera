import abc


class ContactServiceInterface(abc.ABC):

    @abc.abstractmethod
    def register(self, contact):
        pass

    @abc.abstractmethod
    def handle_heartbeat(self):
        """
        Accept all components of an agent profile and save a new agent or register an updated heartbeat.
        :return: the agent object, instructions to execute
        """
        pass

    @abc.abstractmethod
    def build_filename(self):
        pass
