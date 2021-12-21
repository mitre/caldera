import operator

import aiohttp_apispec
from aiohttp import web

import app
from app.api.v2 import security
from app.api.v2.handlers.base_api import BaseApi
from app.api.v2.schemas.caldera_info_schemas import CalderaInfoSchema


class HealthApi(BaseApi):
    def __init__(self, services):
        super().__init__(auth_svc=services['auth_svc'])
        self._app_svc = services['app_svc']

    def add_routes(self, app: web.Application):
        router = app.router
        router.add_get('/health', security.authentication_exempt(self.get_health_info))

    @aiohttp_apispec.docs(tags=['health'],
                          summary='Health endpoints returns the status of CALDERA',
                          description='Returns the status of CALDERA and additional details including versions of system components')
    @aiohttp_apispec.response_schema(CalderaInfoSchema, 200, description='Includes all loaded plugins and system components.')
    async def get_health_info(self, request):
        loaded_plugins_sorted = sorted(self._app_svc.get_loaded_plugins(), key=operator.attrgetter('name'))

        mapping = {
            'application': 'CALDERA',
            'version': app.get_version(),
            'plugins': loaded_plugins_sorted
        }

        return web.json_response(CalderaInfoSchema().dump(mapping))
