import abc


class DataServiceInterface(abc.ABC):

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

    @abc.abstractmethod
    def apply(self, collection):
        """
        Add a new collection to RAM
        :param collection:
        :return:
        """
        pass

    @abc.abstractmethod
    def load_data(self, plugins):
        """
        Non-blocking read all the data sources to populate the object store
        :return: None
        """
        pass

    @abc.abstractmethod
    def reload_data(self, plugins):
        """
        Blocking read all the data sources to populate the object store
        :return: None
        """
        pass

    @abc.abstractmethod
    def store(self, c_object):
        """
        Accept any c_object type and store it (create/update) in RAM
        :param c_object:
        :return: a single c_object
        """
        pass

    @abc.abstractmethod
    def locate(self, object_name, match):
        """
        Find all c_objects which match a search. Return all c_objects if no match.
        :param object_name:
        :param match: dict()
        :return: a list of c_object types
        """
        pass

    @abc.abstractmethod
    def remove(self, object_name, match):
        """
        Remove any c_objects which match a search
        :param object_name:
        :param match: dict()
        :return:
        """
        pass
