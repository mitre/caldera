import copy
import itertools
import re
from base64 import b64decode
from datetime import datetime
from importlib import import_module

from app.service.base_service import BaseService
from app.utility.rule import RuleSet


class PlanningService(BasePlanningService):

    def __init__(self):
        self.log = self.add_service('planning_svc', self)

    async def get_links(self, operation, agent, phase=None, trim=False):
        """
        For an operation, phase and agent combination, create links (that can be executed)
        :param operation:
        :param agent:
        :param phase:
        :param trim: call trim_links() call on list of links before returning
        :return: a list of links
        """
        await self.get_service('parsing_svc').parse_facts(operation)
        operation = (await self.get_service('data_svc').explode_operation(criteria=dict(id=operation['id'])))[0]

        if (not agent['trusted']) and (not operation['allow_untrusted']):
            self.log.debug('Agent %s untrusted: no link created' % agent['paw'])
            return []

        if phase:
            abilities = [i for p, v in operation['adversary']['phases'].items() if p <= phase for i in v]
        else:
            abilities = [i for p, v in operation['adversary']['phases'].items() for i in v]
    
        abilities = sorted(abilities, key=lambda i: i['id'])
        link_status = await self._default_link_status(operation)
        links = []
        for a in await self.get_service('agent_svc').capable_agent_abilities(abilities, agent):
            links.append(await self.get_link(operation, agent, a))
        if trim:
            ability_requirements = {ab['id']: ab.get('requirements', []) for ab in abilities}
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
        if (not agent['trusted']) and (not operation['allow_untrusted']):
            self.log.debug('Agent %s untrusted: no cleanup-link created' % agent['paw'])
            return
        links = []
        for link in await self.get_service('data_svc').explode_chain(criteria=dict(paw=agent['paw'],
                                                                                   op_id=operation['id'])):
            ability = (await self.get_service('data_svc').explode_abilities(criteria=dict(id=link['ability'])))[0]
            if ability['cleanup'] and link['status'] >= 0:
                links.append(await self.get_link(operation, agent, ability, dict(cleanup=1, jitter=0, adversary_map_id=None)))
        return reversed(await self._trim_links(operation, links, agent))
        
    async def get_link(self, operation, agent, ability, fields):
        """
        For an operation, agent, ability combination create link. Any field/values
        in 'fields' dict parameter will overwrite the default link fields
        :param operation:
        :param agent:
        :param ability:
        :param fields:
        :return: link
        """
        # craft link based on default operation, agent and ability values
        link = dict(op_id=operation['id'], paw=agent['paw'], ability=ability['id'],
                    command=ability['test'], executor=ability['executor'], score=0,
                    jitter=self.jitter(operation["jitter"]), decide=datetime.now(),
                    status=await self._default_link_status(operation),
                    adversary_map_id=ability["adversary_map_id"])

        # if caller further specifies modified link fields, update link
        link.update(fields)

        return link

    """ PRIVATE """

    @staticmethod
    async def _sort_links(links):
        """
        Sort links by their score then by the order they are defined in an adversary profile
        """
        return sorted(links, key=lambda k: (-k['score'], k['adversary_map_id']))

    async def _default_link_status(self, operation):
        return self.LinkState.EXECUTE.value if operation['autonomous'] else self.LinkState.PAUSE.value
