import aiohttp_apispec
from aiohttp import web

from app.api.v2.handlers.base_object_api import BaseObjectApi
from app.api.v2.managers.base_api_manager import BaseApiManager
from app.api.v2.schemas.base_schemas import BaseGetAllQuerySchema, BaseGetOneQuerySchema
from app.objects.c_plugin import Plugin, PluginSchema


class PluginApi(BaseObjectApi):
    def __init__(self, services):
        super().__init__(description='plugins', obj_class=Plugin, schema=PluginSchema, ram_key='plugins',
                         id_property='name', auth_svc=services['auth_svc'])
        self._api_manager = BaseApiManager(data_svc=services['data_svc'], file_svc=services['file_svc'])

    def add_routes(self, app: web.Application):
        router = app.router
        router.add_get('/plugins', self.get_plugins)
        router.add_get('/plugins/{name}', self.get_plugin_by_name)

    @aiohttp_apispec.docs(tags=['plugins'])
    @aiohttp_apispec.querystring_schema(BaseGetAllQuerySchema)
    @aiohttp_apispec.response_schema(PluginSchema(many=True, partial=True))
    async def get_plugins(self, request: web.Request):
        plugins = await self.get_all_objects(request)
        return web.json_response(plugins)

    @aiohttp_apispec.docs(tags=['plugins'])
    @aiohttp_apispec.querystring_schema(BaseGetOneQuerySchema)
    @aiohttp_apispec.response_schema(PluginSchema(partial=True))
    async def get_plugin_by_name(self, request: web.Request):
        plugin = await self.get_object(request)
        return web.json_response(plugin)
