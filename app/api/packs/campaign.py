import asyncio

from aiohttp_jinja2 import template

from app.service.auth_svc import red_authorization
from app.utility.base_world import BaseWorld


class CampaignPack(BaseWorld):

    def __init__(self, services):
        self.display_name = 'campaigns'
        self.access = self.Access.RED
        self.endpoints = dict(
            agents='/%s/agents' % self.display_name,
            profiles='/%s/profiles' % self.display_name,
            operations='/%s/operations' % self.display_name
        )
        self.app_svc = services.get('app_svc')
        self.data_svc = services.get('data_svc')
        self.rest_svc = services.get('rest_svc')
        self._search = dict(access=(self.Access.RED, self.Access.APP))
        asyncio.get_event_loop().create_task(self.enable)

    async def enable(self):
        self.app_svc.application.router.add_route('GET', self.endpoints['agents'], self._section_agent)
        self.app_svc.application.router.add_route('GET', self.endpoints['profiles'], self._section_profiles)
        self.app_svc.application.router.add_route('GET', self.endpoints['operations'], self._section_operations)

    """ PRIVATE """

    @red_authorization
    @template('agents.html')
    async def _section_agent(self, request):
        agents = [h.display for h in await self.data_svc.locate('agents', match=self._search)]
        return dict(agents=agents)

    @red_authorization
    @template('profiles.html')
    async def _section_profiles(self, request):
        abilities = await self.data_svc.locate('abilities', match=self._search)
        tactics = set([a.tactic.lower() for a in abilities])
        payloads = await self.rest_svc.list_payloads()
        adversaries = [a.display for a in await self.data_svc.locate('adversaries', match=self._search)]
        return dict(adversaries=adversaries, exploits=[a.display for a in abilities], payloads=payloads,
                    tactics=tactics)

    @red_authorization
    @template('operations.html')
    async def _section_operations(self, request):
        hosts = [h.display for h in await self.data_svc.locate('agents', match=self._search)]
        groups = list(set(([h['group'] for h in hosts])))
        adversaries = [a.display for a in await self.data_svc.locate('adversaries', match=self._search)]
        sources = [s.display for s in await self.data_svc.locate('sources', match=self._search)]
        planners = [p.display for p in await self.data_svc.locate('planners')]
        obfuscators = [o.display for o in await self.data_svc.locate('obfuscators')]
        operations = [o.display for o in await self.data_svc.locate('operations')]
        return dict(operations=operations, groups=groups, adversaries=adversaries, sources=sources, planners=planners,
                    obfuscators=obfuscators)
