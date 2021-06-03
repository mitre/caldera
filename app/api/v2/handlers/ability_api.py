import aiohttp_apispec
from aiohttp import web

from app.api.v2.handlers.base_api import BaseApi
from app.api.v2.managers.base_api_manager import BaseApiManager
from app.api.v2.responses import JsonHttpNotFound
from app.api.v2.schemas.base_schemas import BaseGetAllQuerySchema, BaseGetOneQuerySchema
from app.objects.c_ability import AbilitySchema


class AbilityApi(BaseApi):
    def __init__(self, services):
        super().__init__(auth_svc=services['auth_svc'])
        self._api_manager = BaseApiManager(data_svc=services['data_svc'])

    def add_routes(self, app: web.Application):
        router = app.router
        router.add_get('/abilities', self.get_abilities)
        router.add_get('/abilities/{ability_id}', self.get_ability_by_id)
        router.add_post('/abilities', self.post_abilities)
        router.add_put('/abilities/{ability_id}', self.put_ability_by_id)
        router.add_patch('/abilities/{ability_id}', self.patch_ability_by_id)
        router.add_delete('/abilities/{ability_id}', self.delete_ability_by_id)

    @aiohttp_apispec.docs(tags=['abilities'])
    @aiohttp_apispec.querystring_schema(BaseGetAllQuerySchema)
    @aiohttp_apispec.response_schema(AbilitySchema(many=True))
    async def get_abilities(self, request: web.Request):
        sort = request['querystring'].get('sort', 'name')
        include = request['querystring'].get('include')
        exclude = request['querystring'].get('exclude')

        abilities = self._api_manager.get_objects_with_filters('abilities', sort=sort, include=include, exclude=exclude)
        return web.json_response(abilities)

    @aiohttp_apispec.docs(tags=['abilities'])
    @aiohttp_apispec.querystring_schema(BaseGetOneQuerySchema)
    @aiohttp_apispec.response_schema(AbilitySchema)
    async def get_ability_by_id(self, request: web.Request):
        ability_id = request.match_info['ability_id']
        include = request['querystring'].get('include')
        exclude = request['querystring'].get('exclude')

        search = dict(ability_id=ability_id)

        ability = self._api_manager.get_object_with_filters('abilities', search=search, include=include, exclude=exclude)
        if not ability:
            raise JsonHttpNotFound(f'Planner not found: {ability_id}')

        return web.json_response(ability)

    @aiohttp_apispec.docs(tags=['abilities'])
    @aiohttp_apispec.querystring_schema(BaseGetAllQuerySchema)
    @aiohttp_apispec.response_schema(AbilitySchema(many=True))
    async def post_abilities(self, request: web.Request):
        pass

    @aiohttp_apispec.docs(tags=['abilities'])
    @aiohttp_apispec.querystring_schema(BaseGetOneQuerySchema)
    @aiohttp_apispec.response_schema(AbilitySchema)
    async def put_ability_by_id(self, request: web.Request):
        pass

    @aiohttp_apispec.docs(tags=['abilities'])
    @aiohttp_apispec.querystring_schema(BaseGetOneQuerySchema)
    @aiohttp_apispec.response_schema(AbilitySchema)
    async def patch_ability_by_id(self, request: web.Request):
        pass

    @aiohttp_apispec.docs(tags=['abilities'])
    @aiohttp_apispec.querystring_schema(BaseGetOneQuerySchema)
    @aiohttp_apispec.response_schema(AbilitySchema)
    async def delete_ability_by_id(self, request: web.Request):
        pass
