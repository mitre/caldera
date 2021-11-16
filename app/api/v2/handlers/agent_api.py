import aiohttp_apispec
from aiohttp import web

from app.api.v2.handlers.base_object_api import BaseObjectApi
from app.api.v2.managers.agent_api_manager import AgentApiManager
from app.api.v2.schemas.deploy_command_schemas import DeployCommandsSchema
from app.api.v2.schemas.base_schemas import BaseGetAllQuerySchema, BaseGetOneQuerySchema
from app.objects.c_agent import Agent, AgentSchema


class AgentApi(BaseObjectApi):
    def __init__(self, services):
        super().__init__(description='agent', obj_class=Agent, schema=AgentSchema, ram_key='agents',
                         id_property='paw', auth_svc=services['auth_svc'])
        self._api_manager = AgentApiManager(data_svc=services['data_svc'], file_svc=services['file_svc'])

    def add_routes(self, app: web.Application):
        router = app.router
        router.add_get('/agents', self.get_agents)
        router.add_get('/agents/{paw}', self.get_agent_by_id)
        router.add_post('/agents', self.create_agent)
        router.add_patch('/agents/{paw}', self.update_agent)
        router.add_put('/agents/{paw}', self.create_or_update_agent)
        router.add_delete('/agents/{paw}', self.delete_agent)

        router.add_get('/deploy_commands', self.get_deploy_commands)
        router.add_get('/deploy_commands/{ability_id}', self.get_deploy_commands_for_ability)

    @aiohttp_apispec.docs(tags=['agents'])
    @aiohttp_apispec.querystring_schema(BaseGetAllQuerySchema)
    @aiohttp_apispec.response_schema(AgentSchema(many=True, partial=True))
    async def get_agents(self, request: web.Request):
        agents = await self.get_all_objects(request)
        return web.json_response(agents)

    @aiohttp_apispec.docs(tags=['agents'])
    @aiohttp_apispec.querystring_schema(BaseGetOneQuerySchema)
    @aiohttp_apispec.response_schema(AgentSchema(partial=True))
    async def get_agent_by_id(self, request: web.Request):
        agent = await self.get_object(request)
        return web.json_response(agent)

    @aiohttp_apispec.docs(tags=['agents'])
    @aiohttp_apispec.request_schema(AgentSchema)
    @aiohttp_apispec.response_schema(AgentSchema)
    async def create_agent(self, request: web.Request):
        agent = await self.create_object(request)
        return web.json_response(agent.display)

    @aiohttp_apispec.docs(tags=['agents'])
    @aiohttp_apispec.request_schema(AgentSchema(partial=True, only=['group',
                                                                    'trusted',
                                                                    'sleep_min',
                                                                    'sleep_max',
                                                                    'watchdog',
                                                                    'pending_contact']))
    @aiohttp_apispec.response_schema(AgentSchema)
    async def update_agent(self, request: web.Request):
        agent = await self.update_object(request)
        return web.json_response(agent.display)

    @aiohttp_apispec.docs(tags=['agents'])
    @aiohttp_apispec.request_schema(AgentSchema(partial=True))
    @aiohttp_apispec.response_schema(AgentSchema)
    async def create_or_update_agent(self, request: web.Request):
        agent = await self.create_or_update_object(request)
        return web.json_response(agent.display)

    @aiohttp_apispec.docs(tags=['agents'])
    @aiohttp_apispec.response_schema(AgentSchema)
    async def delete_agent(self, request: web.Request):
        await self.delete_object(request)
        return web.HTTPNoContent()

    @aiohttp_apispec.docs(tags=['agents'])
    @aiohttp_apispec.response_schema(DeployCommandsSchema)
    async def get_deploy_commands(self, request: web.Request):
        deploy_commands = await self._api_manager.get_deploy_commands()
        return web.json_response(deploy_commands)

    @aiohttp_apispec.docs(tags=['agents'])
    @aiohttp_apispec.response_schema(DeployCommandsSchema)
    async def get_deploy_commands_for_ability(self, request: web.Request):
        ability_id = request.match_info.get('ability_id')
        deploy_commands = await self._api_manager.get_deploy_commands(ability_id)
        return web.json_response(deploy_commands)
