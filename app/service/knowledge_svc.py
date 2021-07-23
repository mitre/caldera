from importlib import import_module

from app.objects.secondclass.c_fact import Fact
from app.objects.secondclass.c_relationship import Relationship
from app.objects.secondclass.c_rule import Rule
from app.service.interfaces.i_knowledge_svc import KnowledgeServiceInterface
from app.utility.base_knowledge_svc import BaseKnowledgeService
from app.utility.base_service import BaseService


class KnowledgeService(KnowledgeServiceInterface, BaseService):

    def __init__(self):
        self.log = self.add_service('knowledge_svc', self)
        target_module = self.get_config('app.knowledge_svc.module')
        try:
            self.__loaded_knowledge_module = self._load_module(target_module, {})
        except Exception as e:
            self.log.warning(f"Unable to properly load knowledge service module "
                             f"{self.get_config('app.knowledge_svc.module')} ({e}). Reverting to default.")
            self.__loaded_knowledge_module = BaseKnowledgeService()

    @staticmethod
    def _load_module(module_type, module_info):
        module = import_module(module_info['module'])
        return getattr(module, module_type)(module_info)

    async def add_fact(self, fact, constraints=None):
        if isinstance(fact, Fact):
            return await self.__loaded_knowledge_module._add_fact(fact, constraints)

    async def update_fact(self, criteria, updates):
        return await self.__loaded_knowledge_module._update_fact(criteria, updates)

    async def get_facts(self, criteria, restrictions=None):
        """
        # Becomes a powerful function, because it sorts and filters out facts based on
        # input (values, groupings) as well as underlying mechanisms such as fact mutexs
        """
        return await self.__loaded_knowledge_module._get_facts(criteria, restrictions)

    async def delete_fact(self, criteria):
        return await self.__loaded_knowledge_module._delete_fact(criteria)

    async def get_meta_facts(self, meta_fact=None, agent=None, group=None):
        return await self.__loaded_knowledge_module._get_meta_facts(meta_fact, agent, group)

    async def get_fact_origin(self, fact):
        """
        # Retrieve the specific origin of a fact. If it was learned in the current operation, parse through
        # links to identify the host it was discovered on.
        """
        return await self.__loaded_knowledge_module._get_fact_origin(fact)

    async def check_fact_exists(self, fact, listing=None):
        """
        Check to see if a fact already exists in the knowledge store, or if a listing is provided, in said listing
        :param fact: The fact to check for
        :param listing: Optional specific listing to examine
        :return: Bool indicating whether or not the fact is already present
        """
        searchable = fact.display
        if not listing:
            results = await self.get_facts(criteria=searchable)
        else:
            results = any([fact == x for x in listing])
        if results:
            return True
        return False

    # -- Relationships --

    async def get_relationships(self, criteria, restrictions=None):
        return await self.__loaded_knowledge_module._get_relationships(criteria, restrictions)

    async def add_relationship(self, relationship, constraints=None):
        if isinstance(relationship, Relationship):
            return await self.__loaded_knowledge_module._add_relationship(relationship, constraints)

    async def update_relationship(self, criteria, updates):
        return await self.__loaded_knowledge_module._update_relationship(criteria, updates)

    async def delete_relationship(self, criteria):
        return await self.__loaded_knowledge_module._delete_relationship(criteria)

    # --- Rules ---
    async def add_rule(self, rule, constraints=None):
        """
        # Add a rule to the knowledge service
        # Args:
        #    rule.action: [DENY, ALLOW, EXCLUSIVE, EXCLUSIVE_TRAIT, EXCLUSIVE_VALUE], 'EXCLUSIVE_*' actions denote that
        #        the trait/value will be made mutually exclusive in its use to the agent/group/operation that is
        #        specified for. Essentially a fact is binded to mutex, and only one action can be using the fact
        #        at any one time.
        """
        if isinstance(rule, Rule):
            return await self.__loaded_knowledge_module._add_rule(rule, constraints)

    async def get_rules(self, criteria, restrictions=None):
        return await self.__loaded_knowledge_module._get_rules(criteria)

    async def delete_rule(self, criteria):
        return await self.__loaded_knowledge_module._delete_rule(criteria)

    async def save_state(self):
        return await self.__loaded_knowledge_module._save_state()

    async def restore_state(self):
        return await self.__loaded_knowledge_module._restore_state()

    async def destroy(self):
        """
        Delete data stores
        """
        return self.__loaded_knowledge_module._destroy()
