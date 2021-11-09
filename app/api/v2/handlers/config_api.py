import aiohttp_apispec
from aiohttp import web

from app.api.v2.handlers.base_api import BaseApi
from app.api.v2.responses import JsonHttpForbidden, JsonHttpNotFound
from app.api.v2.schemas.config_schemas import ConfigUpdateSchema, AgentConfigUpdateSchema
from app.api.v2.managers.config_api_manager import ConfigApiManager, ConfigNotFound, ConfigUpdateNotAllowed


class ConfigApi(BaseApi):
    def __init__(self, services):
        super().__init__(auth_svc=services['auth_svc'])
        self._api_manager = ConfigApiManager(data_svc=services['data_svc'], file_svc=services['file_svc'])

    def add_routes(self, app: web.Application):
        router = app.router
        router.add_get('/config/{name}', self.get_config_with_name)
        router.add_patch('/config/main', self.update_main_config)
        router.add_patch('/config/agents', self.update_agents_config)

    @aiohttp_apispec.docs(tags=['config'], summary='Retrieve Config',
                          parameters=[{
                              'in': 'path',
                              'name': 'name',
                              'schema': {'type': 'string'},
                              'required': 'true',
                              'description': 'Name of the configuration file to be retrieved.'
                          }],
                          description='Retrieves configuration by name, as specified by {name} in the request url.')
    async def get_config_with_name(self, request):
        config_name = request.match_info['name']

        try:
            config = self._api_manager.get_filtered_config(config_name)
        except ConfigNotFound:
            raise JsonHttpNotFound(f'Config not found: {config_name}')
        return web.json_response(config)

    @aiohttp_apispec.docs(tags=['config'], summary='Update Agent Config',
                          description='Use fields from the AgentConfigUpdateSchema in the request body to '
                                      'update the Agent Configuration file.')
    @aiohttp_apispec.request_schema(AgentConfigUpdateSchema)
    @aiohttp_apispec.response_schema(AgentConfigUpdateSchema,
                                     description='The response consists of data from the Agent configuration file '
                                                 'dumped in the AgentConfigUpdateSchema format.')
    async def update_agents_config(self, request):
        schema = AgentConfigUpdateSchema()
        data = await self.parse_json_body(request, schema)

        await self._api_manager.update_global_agent_config(**data)
        agents_config = self._api_manager.get_filtered_config('agents')
        return web.json_response(schema.dump(agents_config))

    @aiohttp_apispec.docs(tags=['config'], summary='Update Main Config',
                          description='Use fields from the ConfigUpdateSchema in the request body to '
                                      'update the main configuration file.')
    @aiohttp_apispec.request_schema(ConfigUpdateSchema)
    async def update_main_config(self, request):
        data = await self.parse_json_body(
            request,
            schema=ConfigUpdateSchema()
        )

        try:
            self._api_manager.update_main_config(
                prop=data['prop'],
                value=data['value']
            )
        except ConfigUpdateNotAllowed as ex:
            raise JsonHttpForbidden(
                error='Update not allowed',
                details={'property': ex.property}
            )

        return web.json_response(self._api_manager.get_filtered_config('main'))
