import abc


class PlanningServiceInterface(abc.ABC):

    @abc.abstractmethod
    def get_links(self, operation, buckets, agent, trim):
        """
        For an operation and agent combination, create links (that can be executed).
        When no agent is supplied, links for all agents are returned
        :param operation:
        :param buckets:
        :param agent:
        :param trim: call trim_links() on list of links before returning
        :return: a list of links
        """
        pass

    @abc.abstractmethod
    def get_cleanup_links(self, operation, agent):
        """
        For a given operation, create all cleanup links.
        If agent is supplied, only return cleanup links for that agent.
        :param operation:
        :param agent:
        :return: None
        """
        pass

    @abc.abstractmethod
    def generate_and_trim_links(self, agent, operation, abilities, trim):
        pass

    @staticmethod
    @abc.abstractmethod
    def sort_links(self, links):
        """
        Sort links by their score then by the order they are defined in an adversary profile
        """
        pass
