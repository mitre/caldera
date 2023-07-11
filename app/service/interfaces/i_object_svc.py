import abc


class ObjectServiceInterface(abc.ABC):

    @staticmethod
    @abc.abstractmethod
    def destroy():
        """
        Clear out all data
        :return:
        """
        raise NotImplementedError

    @abc.abstractmethod
    def save_state(self):
        """
        Save stored data to disk
        :return:
        """
        raise NotImplementedError

    @abc.abstractmethod
    def restore_state(self):
        """
        Load data from disk
        :return:
        """
        raise NotImplementedError
