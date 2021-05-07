import aiohttp_apispec
from aiohttp import web

from app.api.v2.handlers.base_api import BaseApi
from app.api.v2.responses import JsonHttpForbidden
from app.api.v2.schemas.config_schemas import ConfigUpdateSchema, AgentConfigUpdateSchema
from app.api.v2.managers.config_api_manager import ConfigApiManager, ConfigNotFound, ConfigUpdateNotAllowed


class ConfigApi(BaseApi):
    def __init__(self, services):
        super().__init__()
        self._api_manager = ConfigApiManager(services)  # inject?

    def add_routes(self, app: web.Application):
        router = app.router
        router.add_get('/config/{name}', self.get_config_with_name)
        router.add_patch('/config/main', self.update_main_config)
        router.add_patch('/config/agents', self.update_agents_config)

    @aiohttp_apispec.docs(tags=['config'])
    async def get_config_with_name(self, request):
        config_name = request.match_info['name']

        try:
            config = self._api_manager.get_filtered_config(config_name)
        except ConfigNotFound:
            raise web.HTTPNotFound(text=f'Config not found: {config_name}')
        return web.json_response(config)

    @aiohttp_apispec.docs(tags=['config'])
    @aiohttp_apispec.request_schema(AgentConfigUpdateSchema)
    async def update_agents_config(self, request):
        schema = AgentConfigUpdateSchema()
        data = schema.load(await request.json())

        await self._api_manager.update_global_agent_config(**data)
        agents_config = self._api_manager.get_filtered_config('agents')
        return web.json_response(agents_config)

    @aiohttp_apispec.docs(tags=['config'])
    @aiohttp_apispec.request_schema(ConfigUpdateSchema)
    async def update_main_config(self, request):
        data = ConfigUpdateSchema().load(await request.json())

        try:
            self._api_manager.update_main_config(
                prop=data['prop'],
                value=data['value']
            )
        except ConfigUpdateNotAllowed:
            raise JsonHttpForbidden('Not allowed to update specified property')

        return web.json_response(self._api_manager.get_filtered_config('main'))
