from aiohttp_jinja2 import template

from app.service.auth_svc import check_authorization
from app.utility.base_world import BaseWorld


class CampaignPack(BaseWorld):

    def __init__(self, services):
        self.auth_svc = services.get('auth_svc')
        self.app_svc = services.get('app_svc')
        self.data_svc = services.get('data_svc')
        self.rest_svc = services.get('rest_svc')

    async def enable(self):
        self.app_svc.application.router.add_route('GET', '/campaign/agents', self._section_agent)
        self.app_svc.application.router.add_route('GET', '/campaign/profiles', self._section_profiles)
        self.app_svc.application.router.add_route('GET', '/campaign/operations', self._section_operations)

    """ PRIVATE """

    @check_authorization
    @template('agents.html')
    async def _section_agent(self, request):
        access = dict(access=tuple(await self.auth_svc.get_permissions(request)))
        agents = [h.display for h in await self.data_svc.locate('agents', match=access)]
        return dict(agents=agents)

    @check_authorization
    @template('profiles.html')
    async def _section_profiles(self, request):
        access = dict(access=tuple(await self.auth_svc.get_permissions(request)))
        abilities = await self.data_svc.locate('abilities', match=access)
        tactics = set([a.tactic.lower() for a in abilities])
        payloads = await self.rest_svc.list_payloads()
        adversaries = [a.display for a in await self.data_svc.locate('adversaries', match=access)]
        return dict(adversaries=adversaries, exploits=[a.display for a in abilities], payloads=payloads,
                    tactics=tactics)

    @check_authorization
    @template('operations.html')
    async def _section_operations(self, request):
        access = dict(access=tuple(await self.auth_svc.get_permissions(request)))
        hosts = [h.display for h in await self.data_svc.locate('agents', match=access)]
        groups = list(set(([h['group'] for h in hosts])))
        adversaries = [a.display for a in await self.data_svc.locate('adversaries', match=access)]
        sources = [s.display for s in await self.data_svc.locate('sources', match=access)]
        planners = [p.display for p in await self.data_svc.locate('planners')]
        obfuscators = [o.display for o in await self.data_svc.locate('obfuscators')]
        operations = [o.display for o in await self.data_svc.locate('operations', match=access)]
        return dict(operations=operations, groups=groups, adversaries=adversaries, sources=sources, planners=planners,
                    obfuscators=obfuscators)
