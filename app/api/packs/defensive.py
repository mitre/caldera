from aiohttp_jinja2 import template

from app.service.auth_svc import blue_authorization
from app.utility.base_world import BaseWorld


class DefensivePack(BaseWorld):

    def __init__(self, services):
        self._search = dict(access=(self.Access.BLUE, self.Access.APP))
        self.auth_svc = services.get('auth_svc')
        self.app_svc = services.get('app_svc')
        self.data_svc = services.get('data_svc')
        self.rest_svc = services.get('rest_svc')

    async def enable(self):
        self.app_svc.application.router.add_route('GET', '/defense/agents', self._section_agent)
        self.app_svc.application.router.add_route('GET', '/defense/profiles', self._section_profiles)

    """ PRIVATE """

    @blue_authorization
    @template('agents.html')
    async def _section_agent(self, request):
        agents = [h.display for h in await self.data_svc.locate('agents', match=self._search)]
        return dict(agents=agents)

    @blue_authorization
    @template('profiles.html')
    async def _section_profiles(self, request):
        abilities = await self.data_svc.locate('abilities', match=self._search)
        tactics = set([a.tactic.lower() for a in abilities])
        payloads = await self.rest_svc.list_payloads()
        adversaries = [a.display for a in await self.data_svc.locate('adversaries', match=self._search)]
        return dict(adversaries=adversaries, exploits=[a.display for a in abilities], payloads=payloads,
                    tactics=tactics)
