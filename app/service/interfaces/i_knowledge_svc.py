import abc


class KnowledgeServiceInterface(abc.ABC):

    @abc.abstractmethod
    async def add_fact(self, fact, constraints=None):
        """
        Add a fact to the internal store
        :param fact: Fact to add
        :param constraints: any potential constraints
        """
        pass

    @abc.abstractmethod
    async def update_fact(self, criteria, updates):
        """
        Update a fact in the internal store
        :param criteria: dictionary containing fields to match on
        :param updates: dictionary containing fields to replace
        """
        pass

    @abc.abstractmethod
    async def get_facts(self, criteria, restrictions=None):
        """
        Retrieve a fact from the internal store
        :param criteria: dictionary containing fields to match on
        :return: list of facts matching the criteria
        """
        pass

    @abc.abstractmethod
    async def delete_fact(self, criteria):
        """
        Delete a fact from the internal store
        :param criteria: dictionary containing fields to match on
        """
        pass

    @abc.abstractmethod
    async def get_meta_facts(self, meta_fact=None, agent=None, group=None):
        """Returns the complete set of facts associated with a meta-fact construct"""
        pass

    @abc.abstractmethod
    async def get_fact_origin(self, fact):
        """Retrieve the specific origin of a fact. If it was learned in the current operation, parse through
        links to identify the host it was discovered on."""
        pass

    @abc.abstractmethod
    async def check_fact_exists(self, fact, listing=None):
        """Check to see if a fact already exists in the knowledge store, or if a listing is provided, in said listing"""
        pass

    # -- Relationships API --
    @abc.abstractmethod
    async def get_relationships(self, criteria, restrictions=None):
        """
        Retrieve relationships from the internal store
        :param criteria: dictionary containing fields to match on
        :return: list of matching relationships
        """
        pass

    @abc.abstractmethod
    async def add_relationship(self, relationship, constraints=None):
        """
        Add a relationship to the internal store
        :param relationship: Relationship object to add
        :param constraints: optional constraints on the use of the relationship
        """
        pass

    @abc.abstractmethod
    async def update_relationship(self, criteria, updates):
        """
        Update a relationship in the internal store
        :param criteria: dictionary containing fields to match on
        :param updates: dictionary containing fields to modify
        """
        pass

    @abc.abstractmethod
    async def delete_relationship(self, criteria):
        """
        Remove a relationship from the internal store
        :param criteria: dictionary containing fields to match on
        """
        pass

    # --- Rule API ---
    @abc.abstractmethod
    async def add_rule(self, rule, constraints=None):
        """
        Add a rule to the internal store
        :param rule: Rule object to add
        :param constraints: dictionary containing fields to match on
        """
        pass

    @abc.abstractmethod
    async def get_rules(self, criteria, restrictions=None):
        """
        Retrieve rules from the internal store
        :param criteria: dictionary containing fields to match on
        :return: list of matching rules
        """
        pass

    @abc.abstractmethod
    async def delete_rule(self, criteria):
        """
        Remove a rule from the internal store
        :param criteria: dictionary containing fields to match on
        """
        pass

    async def destroy(self):
        """Delete data stores"""
        pass
