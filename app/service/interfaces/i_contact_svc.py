import abc


class ContactServiceInterface(abc.ABC):

    @abc.abstractmethod
    def register_contact(self, contact):
        raise NotImplementedError

    @abc.abstractmethod
    def register_tunnel(self, tunnel):
        raise NotImplementedError

    @abc.abstractmethod
    def handle_heartbeat(self):
        """
        Accept all components of an agent profile and save a new agent or register an updated heartbeat.
        :return: the agent object, instructions to execute
        """
        raise NotImplementedError

    @abc.abstractmethod
    def build_filename(self):
        raise NotImplementedError
