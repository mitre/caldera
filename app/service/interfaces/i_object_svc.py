import abc


class ObjectServiceInterface(abc.ABC):

    @staticmethod
    @abc.abstractmethod
    def destroy():
        """
        Clear out all data
        :return:
        """
        pass

    @abc.abstractmethod
    def save_state(self):
        """
        Accept all components of an agent profile and save a new agent or register an updated heartbeat.
        :return: the agent object, instructions to execute
        """
        pass

    @abc.abstractmethod
    def restore_state(self):
        pass
