import aiohttp_apispec
from aiohttp import web

from app.api.v2.handlers.base_api import BaseApi
from app.api.v2.managers.ability_api_manager import AbilityApiManager
from app.api.v2.responses import JsonHttpNotFound
from app.api.v2.schemas.base_schemas import BaseGetAllQuerySchema, BaseGetOneQuerySchema
from app.objects.c_ability import AbilitySchema


class AbilityApi(BaseApi):
    def __init__(self, services):
        super().__init__(auth_svc=services['auth_svc'])
        self._api_manager = AbilityApiManager(data_svc=services['data_svc'], rest_svc=services['rest_svc'])

    def add_routes(self, app: web.Application):
        router = app.router
        router.add_get('/abilities', self.get_abilities)
        router.add_get('/abilities/{ability_id}', self.get_ability_by_id)
        router.add_post('/abilities', self.create_abilities)
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

        access = await self.get_request_permissions(request)

        abilities = self._api_manager.get_objects_with_filters('abilities', search=access, sort=sort,
                                                               include=include, exclude=exclude)
        return web.json_response(abilities)

    @aiohttp_apispec.docs(tags=['abilities'])
    @aiohttp_apispec.querystring_schema(BaseGetOneQuerySchema)
    @aiohttp_apispec.response_schema(AbilitySchema)
    async def get_ability_by_id(self, request: web.Request):
        ability_id = request.match_info['ability_id']
        include = request['querystring'].get('include')
        exclude = request['querystring'].get('exclude')

        access = await self.get_request_permissions(request)
        query = dict(ability_id=ability_id)
        search = {**query, **access}

        ability = self._api_manager.get_object_with_filters('abilities', search=search, include=include,
                                                            exclude=exclude)
        if not ability:
            raise JsonHttpNotFound(f'Ability not found: {ability_id}')

        return web.json_response(ability)

    @aiohttp_apispec.docs(tags=['abilities'])
    @aiohttp_apispec.querystring_schema(BaseGetAllQuerySchema)
    @aiohttp_apispec.response_schema(AbilitySchema(many=True))
    async def create_abilities(self, request: web.Request):
        ability_list = await request.json()
        access = await self.get_request_permissions(request)

        source = await self._api_manager.create_abilities(access=access, ability_list=ability_list)

        return web.json_response(source, status=201)

    @aiohttp_apispec.docs(tags=['abilities'])
    @aiohttp_apispec.querystring_schema(BaseGetOneQuerySchema)
    @aiohttp_apispec.response_schema(AbilitySchema)
    async def put_ability_by_id(self, request: web.Request):
        # data = await request.json()
        ability_id = request.match_info['ability_id']
        include = request['querystring'].get('include')
        exclude = request['querystring'].get('exclude')

        search = dict(ability_id=ability_id)

        ability = self._api_manager.get_object_with_filters('abilities', search=search, include=include,
                                                            exclude=exclude)
        if not ability:
            pass
        else:
            pass

    @aiohttp_apispec.docs(tags=['abilities'])
    @aiohttp_apispec.querystring_schema(BaseGetOneQuerySchema)
    @aiohttp_apispec.response_schema(AbilitySchema)
    async def patch_ability_by_id(self, request: web.Request):
        # Check if ability exists
        # If ability exists, update fields.
        # Else, return error.
        pass

    @aiohttp_apispec.docs(tags=['abilities'])
    @aiohttp_apispec.querystring_schema(BaseGetOneQuerySchema)
    @aiohttp_apispec.response_schema(AbilitySchema)
    async def delete_ability_by_id(self, request: web.Request):
        ability_id = request.match_info['ability_id']
        ability_dict = dict(ability_id=ability_id)
        ability = self._api_manager.get_object_with_filters('abilities', search=ability_dict)

        if not ability:
            raise JsonHttpNotFound(f'Ability not found: {ability_id}')

        await self._api_manager.delete_ability(ability_dict)

        return web.Response(status=204)
