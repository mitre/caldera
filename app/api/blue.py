import logging
from aiohttp import web
from aiohttp_jinja2 import template

from app.service.auth_svc import blue_authorization, check_authorization


@template('blue.html')
# @check_authorization
@blue_authorization
async def landing(self, request):
    try:
        search = dict(enabled=True, access=(self.Access.BLUE, self.Access.APP))
        plugins = await self.data_svc.locate('plugins', search)
        return dict(plugins=[p.display for p in plugins])
    except web.HTTPFound as e:
        raise e
    except Exception as e:
        logging.error('[!] landing: %s' % e)
