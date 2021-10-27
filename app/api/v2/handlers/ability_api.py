import aiohttp_apispec
from aiohttp import web

from app.api.v2.handlers.base_object_api import BaseObjectApi
from app.api.v2.managers.ability_api_manager import AbilityApiManager
from app.api.v2.schemas.base_schemas import BaseGetAllQuerySchema, BaseGetOneQuerySchema
from app.objects.c_ability import Ability, AbilitySchema


class AbilityApi(BaseObjectApi):
    def __init__(self, services):
        super().__init__(description='ability', obj_class=Ability, schema=AbilitySchema, ram_key='abilities',
                         id_property='ability_id', auth_svc=services['auth_svc'])
        self._api_manager = AbilityApiManager(data_svc=services['data_svc'], file_svc=services['file_svc'])

    def add_routes(self, app: web.Application):
        router = app.router
        router.add_get('/abilities', self.get_abilities)
        router.add_get('/abilities/{ability_id}', self.get_ability_by_id)
        router.add_post('/abilities', self.create_ability)
        router.add_put('/abilities/{ability_id}', self.create_or_update_ability)
        router.add_patch('/abilities/{ability_id}', self.update_ability)
        router.add_delete('/abilities/{ability_id}', self.delete_ability)

    @aiohttp_apispec.docs(tags=['abilities'])
    @aiohttp_apispec.querystring_schema(BaseGetAllQuerySchema)
    @aiohttp_apispec.response_schema(AbilitySchema(many=True, partial=True))
    async def get_abilities(self, request: web.Request):
        abilities = await self.get_all_objects(request)
        return web.json_response(abilities)

    @aiohttp_apispec.docs(tags=['abilities'])
    @aiohttp_apispec.querystring_schema(BaseGetOneQuerySchema)
    @aiohttp_apispec.response_schema(AbilitySchema(partial=True))
    async def get_ability_by_id(self, request: web.Request):
        ability = await self.get_object(request)
        return web.json_response(ability)

    @aiohttp_apispec.docs(tags=['abilities'], summary='"name", "tactic", and "executors" are all required fields.')
    @aiohttp_apispec.request_schema(AbilitySchema)
    @aiohttp_apispec.response_schema(AbilitySchema)
    async def create_ability(self, request: web.Request):
        ability = await self.create_on_disk_object(request)
        return web.json_response(ability.display)

    @aiohttp_apispec.docs(tags=['abilities'], summary='"name", "tactic", and "executors" are all required fields.')
    @aiohttp_apispec.request_schema(AbilitySchema(partial=True))
    @aiohttp_apispec.response_schema(AbilitySchema)
    async def create_or_update_ability(self, request: web.Request):
        ability = await self.create_or_update_on_disk_object(request)
        return web.json_response(ability.display)

    @aiohttp_apispec.docs(tags=['abilities'])
    @aiohttp_apispec.request_schema(AbilitySchema(partial=True, exclude=['ability_id',
                                                                         'requirements',
                                                                         'additional_info',
                                                                         'access']))
    @aiohttp_apispec.response_schema(AbilitySchema)
    async def update_ability(self, request: web.Request):
        ability = await self.update_on_disk_object(request)
        return web.json_response(ability.display)

    @aiohttp_apispec.docs(tags=['abilities'])
    @aiohttp_apispec.response_schema(AbilitySchema)
    async def delete_ability(self, request: web.Request):
        await self.delete_on_disk_object(request)
        return web.HTTPNoContent()
