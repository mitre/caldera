import logging
from aiohttp import web
from aiohttp_jinja2 import template

from app.service.auth_svc import red_authorization


@red_authorization
@template('red.html')
async def landing(self, request):
    try:
        search = dict(enabled=True, access=(self.Access.RED, self.Access.APP))
        plugins = await self.data_svc.locate('plugins', search)
        return dict(plugins=[p.display for p in plugins])
    except web.HTTPFound as e:
        raise e
    except Exception as e:
        logging.error('[!] landing: %s' % e)


@red_authorization
@template('agents.html')
async def section_agent(self, request):
    agents = [h.display for h in await self.data_svc.locate('agents')]
    return dict(agents=agents)
