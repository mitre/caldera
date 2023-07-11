import abc


class AppServiceInterface(abc.ABC):

    @abc.abstractmethod
    def start_sniffer_untrusted_agents(self):
        """
        Cyclic function that repeatedly checks if there are agents to be marked as untrusted
        :return: None
        """
        raise NotImplementedError

    @abc.abstractmethod
    def find_link(self, unique):
        """
        Locate a given link by its unique property
        :param unique:
        :return:
        """
        raise NotImplementedError

    @abc.abstractmethod
    def find_op_with_link(self, link_id):
        """
        Locate an operation with the given link ID
        :param link_id:
        :return: Operation or None
        """
        raise NotImplementedError

    @abc.abstractmethod
    def run_scheduler(self):
        """
        Kick off all scheduled jobs, as their schedule determines
        :return:
        """
        raise NotImplementedError

    @abc.abstractmethod
    def resume_operations(self):
        """
        Resume all unfinished operations
        :return: None
        """
        raise NotImplementedError

    @abc.abstractmethod
    def load_plugins(self, plugins):
        """
        Store all plugins in the data store
        :return:
        """
        raise NotImplementedError

    @abc.abstractmethod
    def retrieve_compiled_file(self, name, platform, location=''):
        raise NotImplementedError

    @abc.abstractmethod
    def teardown(self):
        raise NotImplementedError

    @abc.abstractmethod
    def register_contacts(self):
        raise NotImplementedError

    @abc.abstractmethod
    def load_plugin_expansions(self, plugins):
        raise NotImplementedError
