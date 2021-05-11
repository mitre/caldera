from importlib import import_module

from app.service.interfaces.i_knowledge_svc import KnowledgeServiceInterface
from app.utility.base_service import BaseService
from app.utility.base_knowledge_svc import BaseKnowledgeService

from app.objects.secondclass.c_fact import Fact
from app.objects.secondclass.c_relationship import Relationship
from app.objects.secondclass.c_rule import Rule

class KnowledgeService(KnowledgeServiceInterface, BaseService):

    def __init__(self):
        self.log = self.add_service('knowledge_svc', self)
        if self.get_config('app.knowledge_svc.module'):
            try:
                self.__loaded_knowledge_module = self.load_module('BaseKnowledgeService', {})
            except Exception as e:
                self.log.warning(f"Unable to properly load knowledge service module "
                                 f"{self.get_config('app.knowledge_svc.module')} ({e}). Reverting to default.")
                self.__loaded_knowledge_module = BaseKnowledgeService()
        else:
            self.__loaded_knowledge_module = BaseKnowledgeService()

    @staticmethod
    async def _load_module(module_type, module_info):
        module = import_module(module_info['module'])
        return getattr(module, module_type)(module_info)

    # -- Fact API --
    async def add_fact(self, fact):
        """facts can now be highly controlled, with visibility at the
        operation level, agent(s) level, or custom groupings"""
        if isinstance(fact, Fact):
            return self.__loaded_knowledge_module._add_fact(fact)

    async def update_fact(self, criteria, updates):
        return self.__loaded_knowledge_module._update_fact(criteria, updates)

    async def get_facts(self, criteria):
        """Becomes a powerful function, because it sorts and filters out facts based on
        input (values, groupings) as well as underlying mechanisms such as fact mutexs"""
        return self.__loaded_knowledge_module._get_facts(criteria)

    async def delete_fact(self, criteria):
        """Delete existing facts based on provided information"""
        return self.__loaded_knowledge_module._delete_fact(criteria)

    async def get_meta_facts(self, meta_fact=None, agent=None, group=None):
        """Returns the complete set of facts associated with a meta-fact construct"""
        return self.__loaded_knowledge_module._get_meta_facts(meta_fact, agent, group)

    async def get_fact_origin(self, fact):
        """Retrieve the specific origin of a fact. If it was learned in the current operation, parse through
        links to identify the host it was discovered on."""
        return self.__loaded_knowledge_module._get_fact_origin(fact)

    # -- Relationships API --

    async def get_relationships(self, criteria):
        return self.__loaded_knowledge_module._get_relationships(criteria)

    async def add_relationship(self, relationship):
        if isinstance(relationship, Relationship):
            return self.__loaded_knowledge_module._add_relationship(relationship)

    async def update_relationship(self, criteria, updates):
        return self.__loaded_knowledge_module._update_relationship(criteria, updates)

    async def delete_relationship(self, criteria):
        return self.__loaded_knowledge_module._delete_relationship(criteria)

    # --- Rule API ---
    async def add_rule(self, rule):
        """
        Args:
            rule.action: [DENY, ALLOW, EXCLUSIVE, EXCLUSIVE_TRAIT, EXCLUSIVE_VALUE], 'EXCLUSIVE_*' actions denote that
                the trait/value will be made mutually exclusive in its use to the agent/group/operation that is
                specified for. Essentially a fact is binded to mutex, and only one action can be using the fact
                at any one time.
        """
        if isinstance(rule, Rule):
            return self.__loaded_knowledge_module._add_rule(rule)

    async def get_rules(self, criteria):
        return self.__loaded_knowledge_module._get_rules(criteria)

    async def delete_rule(self, criteria):
        return self.__loaded_knowledge_module._delete_rule(criteria)

    # --- New Inferencing API ---
    # NOT IMPLEMENTED YET
    async def similar_facts(self, fact, agent, group):
        """return facts that are close to supplied fact.

        Ex:
            - other facts for an agent with given trait/value
            - other facts for the group/agent
            - other facts with same value
        """
        return self.__loaded_knowledge_module._similar_facts(fact, agent, group)

    async def fact_value_distribution(self, trait, agent=None, group=None):
        """return the value distribution for the given fact, and further filtered down
        to agent/group if supplied


        Ex: fact value distribution for 'host.user.name' on group 'workstations':
            --> [{'admin': .4}, {'system': .4}, {'michael': .1}, {'workstation1': .1}]
        """
        return self.__loaded_knowledge_module._fact_value_distribution(trait, agent, group)

    async def best_guess(self, trait, agent=None, group=None):
        """wrapper around 'fact_value_distribution', just returning highest probable value"""
        return self.__loaded_knowledge_module._best_guess(trait, agent, group)

    async def best_facts(self, agent=None, group=None, metric='usage_success'):
        """best facts based on requested metric
        Args:
            metric: ['usage_success', 'most_recent_success', ...]
        """
        return self.__loaded_knowledge_module._best_guess(agent, group, metric)

    async def save_state(self):
        return await self.__loaded_knowledge_module._save_state()

    async def restore_state(self):
        return await self.__loaded_knowledge_module._restore_state()
