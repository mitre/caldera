import operator
from collections import defaultdict

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
        self.app_svc.application.router.add_route('GET', '/campaign/abilities', self._section_abilities)
        self.app_svc.application.router.add_route('GET', '/campaign/adversaries', self._section_profiles)
        self.app_svc.application.router.add_route('GET', '/campaign/operations', self._section_operations)

    @check_authorization
    @template('agents.html')
    async def _section_agent(self, request):
        search = dict(access=tuple(await self.auth_svc.get_permissions(request)))
        agents = [h.display for h in await self.data_svc.locate('agents', match=search)]
        ability_ids = tuple(self.get_config(name='agents', prop='deployments'))
        abilities = await self.data_svc.locate('abilities', match=dict(ability_id=ability_ids))
        agent_config = self.get_config(name='agents')
        return dict(agents=agents, abilities=self._rollup_abilities(abilities), agent_config=agent_config)

    @check_authorization
    @template('abilities.html')
    async def _section_abilities(self, request):
        access = dict(access=tuple(await self.auth_svc.get_permissions(request)))
        abilities = await self.data_svc.locate('abilities', match=access)
        payloads = list(await self.rest_svc.list_payloads())
        platforms = dict()
        for a in abilities:
            for executor in a.executors:
                if executor.platform in platforms:
                    platforms[executor.platform].add(executor.name)
                else:
                    platforms[executor.platform] = set([executor.name])
        for p in platforms:
            platforms[p] = list(platforms[p])
        return dict(platforms=platforms, payloads=payloads)

    @check_authorization
    @template('adversaries.html')
    async def _section_profiles(self, request):
        access = dict(access=tuple(await self.auth_svc.get_permissions(request)))
        abilities = await self.data_svc.locate('abilities', match=access)
        objs = await self.data_svc.locate('objectives', match=access)
        platforms = dict()
        for a in abilities:
            for executor in a.executors:
                if executor.platform in platforms:
                    platforms[executor.platform].add(executor.name)
                else:
                    platforms[executor.platform] = set([executor.name])
        for p in platforms:
            platforms[p] = list(platforms[p])
        tactics = sorted(list(set(a.tactic.lower() for a in abilities)))
        payloads = list(await self.rest_svc.list_payloads())
        adversaries = sorted([a.display for a in await self.data_svc.locate('adversaries', match=access)],
                             key=lambda a: a['name'])
        exploits = sorted([a.display for a in abilities], key=operator.itemgetter('technique_id', 'name'))
        objectives = sorted([a.display for a in objs], key=operator.itemgetter('id', 'name'))
        return dict(adversaries=adversaries, exploits=exploits, payloads=payloads,
                    tactics=tactics, platforms=platforms, objectives=objectives)

    @check_authorization
    @template('operations.html')
    async def _section_operations(self, request):
        def load_usage_markdown(header):
            f = open('plugins/fieldmanual/sphinx-docs/Basic-Usage.md', 'r')
            markdown = []
            seen_header = False
            for x in f:
                if (not seen_header and "## Operations" in x):
                    markdown = []
                    seen_header = True
                elif (seen_header and "## " in x):
                    break
                elif (seen_header):
                    if "*" in x:
                        key, val = x.split(': ')
                        if (key and val):
                            key = key.split("*")[3]
                            val = val.strip("\n")
                        markdown.append({key: val})
            f.close()
            return markdown
        access = dict(access=tuple(await self.auth_svc.get_permissions(request)))
        hosts = [h.display for h in await self.data_svc.locate('agents', match=access)]
        groups = sorted(list(set(([h['group'] for h in hosts]))))
        adversaries = sorted([a.display for a in await self.data_svc.locate('adversaries', match=access)],
                             key=lambda a: a['name'])
        sources = [s.display for s in await self.data_svc.locate('sources', match=access)]
        planners = sorted([p.display for p in await self.data_svc.locate('planners')],
                          key=lambda p: p['name'])
        obfuscators = [o.display for o in await self.data_svc.locate('obfuscators')]
        operations = [o.display for o in await self.data_svc.locate('operations', match=access)]
        usage = load_usage_markdown('operations')
        return dict(operations=operations, groups=groups, adversaries=adversaries, sources=sources, planners=planners,
                    obfuscators=obfuscators, usage=usage)

    @staticmethod
    def _rollup_abilities(abilities):
        rolled = defaultdict(list)
        for a in abilities:
            rolled[a.ability_id].append(a.display)
        return dict(rolled)
