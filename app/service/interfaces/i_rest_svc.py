import abc


class RestServiceInterface(abc.ABC):

    @abc.abstractmethod
    def persist_adversary(self, access, data):
        """
        Save a new adversary from either the GUI or REST API. This writes a new YML file into the core data/ directory.
        :param access
        :param data:
        :return: the ID of the created adversary
        """
        pass

    @abc.abstractmethod
    def update_planner(self, data):
        """
        Update a new planner from either the GUI or REST API with new stopping conditions.
        This overwrites the existing YML file.
        :param data:
        :return: the ID of the created adversary
        """
        pass

    @abc.abstractmethod
    def persist_ability(self, access, data):
        pass

    @abc.abstractmethod
    def persist_source(self, access, data):
        pass

    @abc.abstractmethod
    def delete_agent(self, data):
        pass

    @abc.abstractmethod
    def delete_ability(self, data):
        pass

    @abc.abstractmethod
    def delete_adversary(self, data):
        pass

    @abc.abstractmethod
    def delete_operation(self, data):
        pass

    @abc.abstractmethod
    def display_objects(self, object_name, data):
        pass

    @abc.abstractmethod
    def display_result(self, data):
        pass

    @abc.abstractmethod
    def display_operation_report(self, data):
        pass

    @abc.abstractmethod
    def download_contact_report(self, contact):
        pass

    @abc.abstractmethod
    def update_agent_data(self, data):
        pass

    @abc.abstractmethod
    def update_chain_data(self, data):
        pass

    @abc.abstractmethod
    def create_operation(self, access, data):
        pass

    @abc.abstractmethod
    def create_schedule(self, access, data):
        pass

    @abc.abstractmethod
    def list_payloads(self):
        pass

    @abc.abstractmethod
    def find_abilities(self, paw):
        pass

    @abc.abstractmethod
    def get_potential_links(self, op_id, paw):
        pass

    @abc.abstractmethod
    def apply_potential_link(self, link):
        pass

    @abc.abstractmethod
    def task_agent_with_ability(self, paw, ability_id, obfuscator, facts):
        pass

    @abc.abstractmethod
    def get_link_pin(self, json_data):
        pass

    @abc.abstractmethod
    def construct_agents_for_group(self, group):
        pass

    @abc.abstractmethod
    def update_config(self, data):
        pass

    @abc.abstractmethod
    def update_operation(self, op_id, state, autonomous):
        pass
