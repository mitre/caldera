import abc


class KnowledgeServiceInterface(abc.ABC):

    @abc.abstractmethod
    async def add_fact(self, fact, constraints=None):
        """facts can now be highly controlled, with visibility at the
        operation level, agent(s) level, or custom groupings"""
        pass

    @abc.abstractmethod
    async def update_fact(self, criteria, updates):
        pass

    @abc.abstractmethod
    async def get_facts(self, criteria, restrictions=None):
        """Becomes a powerful function, because it sorts and filters out facts based on
        input (values, groupings) as well as underlying mechanisms such as fact mutexs"""
        pass

    @abc.abstractmethod
    async def delete_fact(self, criteria):
        """Delete existing facts based on provided information"""
        pass

    @abc.abstractmethod
    async def get_meta_facts(self, meta_fact=None, agent=None, group=None):
        """Returns the complete set of facts associated with a meta-fact construct"""
        pass

    @abc.abstractmethod
    async def get_fact_origin(self, fact):
        """Retrieve the specific origin of a fact. If it was learned in the current operation, parse through links to identify the host it was discovered on."""
        pass

    # -- Relationships API --
    @abc.abstractmethod
    async def get_relationships(self, criteria, restrictions=None):
        pass

    @abc.abstractmethod
    async def add_relationship(self, relationship, constraints=None):
        pass

    @abc.abstractmethod
    async def update_relationship(self, criteria, updates):
        pass

    @abc.abstractmethod
    async def delete_relationship(self, criteria):
        pass

    # --- Rule API ---
    @abc.abstractmethod
    async def add_rule(self, rule, constraints=None):
        """
        Args:
            rule.action: [DENY, ALLOW, EXCLUSIVE, EXCLUSIVE_TRAIT, EXCLUSIVE_VALUE], 'EXCLUSIVE_*' actions denote that
                the trait/value will be made mutually exclusive in its use to the agent/group/operation that is
                specified for. Essentially a fact is binded to mutex, and only one action can be using the fact
                at any one time.
        """
        pass

    @abc.abstractmethod
    async def get_rules(self, criteria, restrictions=None):
        pass

    @abc.abstractmethod
    async def delete_rule(self, criteria):
        pass

    # --- New Inferencing API ---
    @abc.abstractmethod
    async def similar_facts(self, fact, agent, group):
        """return facts that are close to supplied fact.


        Ex:
            - other facts for an agent with given trait/value
            - other facts for the group/agent
            - other facts with same value
        """
        pass

    @abc.abstractmethod
    async def fact_value_distribution(self, criteria, agent=None, group=None):
        """return the value distribution for the given fact, and further filtered down
        to agent/group if supplied


        Ex: fact value distribution for 'host.user.name' on group 'workstations':
            --> [{'admin': .4}, {'system': .4}, {'michael': .1}, {'workstation1': .1}]
        """
        pass

    @abc.abstractmethod
    async def best_guess(self, criteria, agent=None, group=None):
        """wrapper around 'fact_value_distribution', just returning highest probable value"""
        pass

    @abc.abstractmethod
    async def best_facts(self, agent=None, group=None, metric='usage_success'):
        """best facts based on requested metric


        Args:
            metric: ['usage_success', 'most_recent_success', ...]
        """
        pass
