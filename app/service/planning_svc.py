import copy
import itertools
import re
from base64 import b64decode
from datetime import datetime

from app.service.base_service import BaseService
from app.service.base_planning_svc import BasePlanningService
from app.utility.rule import RuleSet


class PlanningService(BasePlanningService):

    def __init__(self):
        self.log = self.add_service('planning_svc', self)

    async def get_links(self, operation, agent, phase=None, trim=True):
        """
        For an operation, phase and agent combination, create links (that can be executed)
        :param operation:
        :param agent:
        :param phase:
        :param trim: call trim_links() call on list of links before returning
        :return: a list of links
        """
        await self.get_service('parsing_svc').parse_facts(operation)
        operation = (await self.get_service('data_svc').explode('operation', criteria=dict(id=operation['id'])))[0]

        if (not agent.trusted) and (not operation['allow_untrusted']):
            self.log.debug('Agent %s untrusted: no link created' % agent.paw)
            return []

        if phase:
            abilities = [i for p, v in operation['adversary'].phases.items() if p <= phase for i in v]
        else:
            abilities = [i for p, v in operation['adversary'].phases.items() for i in v]
    
        link_status = await self._default_link_status(operation)
        links = []
        for a in await self.get_service('agent_svc').capable_agent_abilities(abilities, agent):
            links.append(await self.get_link(operation, agent.paw, a))
        if trim:
            ability_requirements = {ab.unique: ab.requirements for ab in abilities}
            links[:] = await self.trim_links(operation, agent, links, ability_requirements)
        return await self._sort_links(links)

    async def get_cleanup_links(self, operation, agent):
        """
        For a given operation, create all cleanup links
        :param operation:
        :param agent:
        :return: None
        """
        link_status = await self._default_link_status(operation)
        if (not agent.trusted) and (not operation['allow_untrusted']):
            self.log.debug('Agent %s untrusted: no cleanup-link created' % agent.paw)
            return
        links = []
        for link in await self.get_service('data_svc').explode('chain', criteria=dict(paw=agent.paw, op_id=operation['id'])):
            ability = (await self.get_service('data_svc').locate('abilities', match=dict(unique=link['ability'])))[0]
            if ability.cleanup and link['status'] >= 0:
                links.append(await self.get_link(operation, agent.paw, ability, dict(cleanup=1,
                                                                                    command=ability.cleanup,
                                                                                    jitter=0)))
        return reversed(await self.trim_links(operation, agent, links))
        
    async def get_link(self, operation, agent_paw, ability, fields=None):
        """
        :param operation: dict
        :param agent_paw: agent paw (str)
        :param ability: dict
        """
        #TODO: reduce what the default fields/values in a link will be. For instance, 'adversary_map_id'
        # shouldnt be in there by default and 1 of 2 main functions (get_cleanup_links()) doesnt use it
        
        # craft link based on default operation, agent and ability values
        link = dict(op_id=operation['id'], paw=agent_paw, ability=ability.unique,
                    command=ability.test, executor=ability.executor, score=0,
                    jitter=self.jitter(operation["jitter"]), decide=datetime.now(),
                    status=await self._default_link_status(operation))
        # if caller further specifies modified link fields, update link
        if fields:
            link.update(fields)
        return link
    
    """ PRIVATE """

    @staticmethod
    async def _sort_links(links):
        """
        Sort links by their score then by the order they are defined in an adversary profile
        """
        return sorted(links, key=lambda k: (-k['score']))

    async def _default_link_status(self, operation):
        return self.LinkState.EXECUTE.value if operation['autonomous'] else self.LinkState.PAUSE.value
