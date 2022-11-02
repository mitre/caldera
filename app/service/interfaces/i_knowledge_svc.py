import abc
from app.service.interfaces.i_object_svc import ObjectServiceInterface


class KnowledgeServiceInterface(ObjectServiceInterface):

    @abc.abstractmethod
    async def add_fact(self, fact, constraints=None):
        """
        Add a fact to the internal store

        :param fact: Fact to add
        :param constraints: any potential constraints
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def update_fact(self, criteria, updates):
        """
        Update a fact in the internal store

        :param criteria: dictionary containing fields to match on
        :param updates: dictionary containing fields to replace
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def get_facts(self, criteria, restrictions=None):
        """
        Retrieve a fact from the internal store

        :param criteria: dictionary containing fields to match on
        :return: list of facts matching the criteria
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def delete_fact(self, criteria):
        """
        Delete a fact from the internal store

        :param criteria: dictionary containing fields to match on
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def get_meta_facts(self, meta_fact=None, agent=None, group=None):
        """Returns the complete set of facts associated with a meta-fact construct [In Development]"""
        raise NotImplementedError

    @abc.abstractmethod
    async def get_fact_origin(self, fact):
        """
        Identify the place where a fact originated, either the source that loaded it or its original link

        :param fact: Fact to get origin for (can be either a trait string or a full blown fact)
        :return: tuple - (String of either origin source id or origin link id, fact origin type)"""
        raise NotImplementedError

    @abc.abstractmethod
    async def check_fact_exists(self, fact, listing=None):
        """
        Check to see if a fact already exists in the knowledge store, or if a listing is provided, in said listing

        :param fact: The fact to check for
        :param listing: Optional specific listing to examine
        :return: Bool indicating whether or not the fact is already present
        """
        raise NotImplementedError

    # -- Relationships API --
    @abc.abstractmethod
    async def get_relationships(self, criteria, restrictions=None):
        """
        Retrieve relationships from the internal store

        :param criteria: dictionary containing fields to match on
        :return: list of matching relationships
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def add_relationship(self, relationship, constraints=None):
        """
        Add a relationship to the internal store

        :param relationship: Relationship object to add
        :param constraints: optional constraints on the use of the relationship
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def update_relationship(self, criteria, updates):
        """
        Update a relationship in the internal store

        :param criteria: dictionary containing fields to match on
        :param updates: dictionary containing fields to modify
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def delete_relationship(self, criteria):
        """
        Remove a relationship from the internal store

        :param criteria: dictionary containing fields to match on
        """
        raise NotImplementedError

    # --- Rule API ---
    @abc.abstractmethod
    async def add_rule(self, rule, constraints=None):
        """
        Add a rule to the internal store

        :param rule: Rule object to add
        :param constraints: dictionary containing fields to match on
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def get_rules(self, criteria, restrictions=None):
        """
        Retrieve rules from the internal store

        :param criteria: dictionary containing fields to match on
        :return: list of matching rules
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def delete_rule(self, criteria):
        """
        Remove a rule from the internal store

        :param criteria: dictionary containing fields to match on
        """
        raise NotImplementedError
