import logging
from aiohttp import web
from aiohttp_jinja2 import template

from app.service.auth_svc import red_authorization
from app.utility.base_world import BaseWorld

search = dict(access=(BaseWorld.Access.RED, BaseWorld.Access.APP))


@red_authorization
@template('red.html')
async def landing(self, request):
    try:
        s = {**search, **dict(enabled=True)}
        plugins = await self.data_svc.locate('plugins', s)
        return dict(plugins=[p.display for p in plugins])
    except web.HTTPFound as e:
        raise e
    except Exception as e:
        logging.error('[!] landing: %s' % e)


@red_authorization
@template('agents.html')
async def section_agent(self, request):
    agents = [h.display for h in await self.data_svc.locate('agents', match=search)]
    return dict(agents=agents)


@red_authorization
@template('profiles.html')
async def section_profiles(self, request):
    abilities = await self.data_svc.locate('abilities', match=search)
    tactics = set([a.tactic.lower() for a in abilities])
    payloads = await self.rest_svc.list_payloads()
    adversaries = [a.display for a in await self.data_svc.locate('adversaries', match=search)]
    return dict(adversaries=adversaries, exploits=[a.display for a in abilities], payloads=payloads, tactics=tactics)


@red_authorization
@template('sources.html')
async def section_sources(self, request):
    sources = [s.display for s in await self.data_svc.locate('sources', match=search)]
    return dict(sources=sources)


@red_authorization
@template('operations.html')
async def section_operations(self, request):
    hosts = [h.display for h in await self.data_svc.locate('agents')]
    groups = list(set(([h['group'] for h in hosts])))
    adversaries = [a.display for a in await self.data_svc.locate('adversaries')]
    sources = [s.display for s in await self.data_svc.locate('sources')]
    planners = [p.display for p in await self.data_svc.locate('planners')]
    obfuscators = [o.display for o in await self.data_svc.locate('obfuscators') if not o.hidden]
    operations = [o.display for o in await self.data_svc.locate('operations')]
    return dict(operations=operations, groups=groups, adversaries=adversaries, sources=sources, planners=planners,
                obfuscators=obfuscators)
