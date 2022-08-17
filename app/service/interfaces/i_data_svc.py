import abc
from app.service.interfaces.i_object_svc import ObjectServiceInterface


class DataServiceInterface(ObjectServiceInterface):

    @abc.abstractmethod
    def apply(self, collection):
        """
        Add a new collection to RAM

        :param collection:
        :return:
        """
        raise NotImplementedError

    @abc.abstractmethod
    def load_data(self, plugins):
        """
        Non-blocking read all the data sources to populate the object store

        :return: None
        """
        raise NotImplementedError

    @abc.abstractmethod
    def reload_data(self, plugins):
        """
        Blocking read all the data sources to populate the object store

        :return: None
        """
        raise NotImplementedError

    @abc.abstractmethod
    def store(self, c_object):
        """
        Accept any c_object type and store it (create/update) in RAM

        :param c_object:
        :return: a single c_object
        """
        raise NotImplementedError

    @abc.abstractmethod
    def locate(self, object_name, match):
        """
        Find all c_objects which match a search. Return all c_objects if no match.

        :param object_name:
        :param match: dict()
        :return: a list of c_object types
        """
        raise NotImplementedError

    @abc.abstractmethod
    def remove(self, object_name, match):
        """
        Remove any c_objects which match a search

        :param object_name:
        :param match: dict()
        :return:
        """
        raise NotImplementedError
