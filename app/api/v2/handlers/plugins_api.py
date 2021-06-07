import aiohttp_apispec
from aiohttp import web

from app.api.v2.handlers.base_api import BaseApi
from app.api.v2.managers.base_api_manager import BaseApiManager
from app.api.v2.responses import JsonHttpNotFound
from app.api.v2.schemas.base_schemas import BaseGetAllQuerySchema, BaseGetOneQuerySchema
from app.objects.c_plugin import PluginSchema


class PluginApi(BaseApi):
    def __init__(self, services):
        super().__init__(auth_svc=services['auth_svc'])
        self._api_manager = BaseApiManager(data_svc=services['data_svc'])

    def add_routes(self, app: web.Application):
        router = app.router
        router.add_get('/plugins', self.get_plugins)
        router.add_get('/plugins/{plugin_name}', self.get_plugin_by_name)

    @aiohttp_apispec.docs(tags=['plugins'])
    @aiohttp_apispec.querystring_schema(BaseGetAllQuerySchema)
    @aiohttp_apispec.response_schema(PluginSchema(many=True))
    async def get_plugins(self, request: web.Request):
        sort = request['querystring'].get('sort', 'name')
        include = request['querystring'].get('include')

        exclude = request['querystring'].get('exclude')

        access = await self.get_request_permissions(request)

        plugins = self._api_manager.get_objects_with_filters(object_name='plugins', search=access, sort=sort,
                                                             include=include, exclude=exclude)
        return web.json_response(plugins)

    @aiohttp_apispec.docs(tags=['plugins'])
    @aiohttp_apispec.querystring_schema(BaseGetOneQuerySchema)
    @aiohttp_apispec.response_schema(PluginSchema)
    async def get_plugin_by_name(self, request: web.Request):
        plugin_name = request.match_info['plugin_name']
        include = request['querystring'].get('include')
        exclude = request['querystring'].get('exclude')

        access = await self.get_request_permissions(request)
        query = dict(name=plugin_name)
        search = {**query, **access}

        plugin = self._api_manager.get_object_with_filters(object_name='plugins', search=search,
                                                           include=include, exclude=exclude)
        if not plugin:
            raise JsonHttpNotFound(f'Plugin not found: {plugin_name}')

        return web.json_response(plugin)
