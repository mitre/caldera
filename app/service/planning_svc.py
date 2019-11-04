import copy
import itertools
import re
from base64 import b64decode

from app.objects.c_link import Link
from app.utility.base_service import BaseService
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
        :param trim: call trim_links() on list of links before returning
        :return: a list of links
        """
        if (not agent.trusted) and (not operation.allow_untrusted):
            self.log.debug('Agent %s untrusted: no link created' % agent.paw)
            return []

        if phase:
            abilities = [i for p, v in operation['adversary'].phases.items() if p <= phase for i in v]
        else:
            abilities = [i for p, v in operation['adversary'].phases.items() for i in v]
    
        link_status = await self._default_link_status(operation)
        links = []
        for a in await agent.capabilities(abilities):
            links.append(
                 Link(operation=operation.name, command=a.test, paw=agent.paw, score=0, ability=a,
                     status=link_status, jitter=self.jitter(operation.jitter))
            )
        if trim:
            ability_requirements = {ab.unique: ab.requirements for ab in abilities}
            links[:] = await self.trim_links(operation, links, agent, ability_requirements)

        return await self._sort_links(links)

    async def get_cleanup_links(self, operation, agent):
        """
        For a given operation, create all cleanup links
        :param operation:
        :param agent:
        :return: None
        """
        link_status = await self._default_link_status(operation)
        if (not agent.trusted) and (not operation.allow_untrusted):
            self.log.debug('Agent %s untrusted: no cleanup-link created' % agent.paw)
            return
        links = []
        for link in [l for l in operation.chain if l.paw == agent.paw]:
            ability = (await self.get_service('data_svc').locate('abilities', match=dict(unique=link.ability.unique)))[0]
            if ability.cleanup and link.status >= 0:
                links.append(Link(operation=operation.name, command=ability.cleanup, paw=agent.paw, cleanup=1,
                                  ability=ability, score=0, jitter=0, status=link_status))
        return reversed(await self.trim_links(operation, links, agent))

    """ PRIVATE """

    @staticmethod
    async def _sort_links(links):
        """
        Sort links by their score then by the order they are defined in an adversary profile
        """
        return sorted(links, key=lambda k: (-k.score))

    async def _default_link_status(self, operation):
        return self.LinkState.EXECUTE.value if operation['autonomous'] else self.LinkState.PAUSE.value
