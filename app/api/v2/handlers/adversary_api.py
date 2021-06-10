import aiohttp_apispec
from aiohttp import web

from app.api.v2.handlers.base_api import BaseApi
from app.api.v2.managers.adversary_api_manager import AdversaryApiManager
from app.api.v2.responses import JsonHttpBadRequest, JsonHttpForbidden, JsonHttpNotFound
from app.api.v2.schemas.base_schemas import BaseGetAllQuerySchema, BaseGetOneQuerySchema
from app.objects.c_adversary import AdversarySchema


class AdversaryApi(BaseApi):
    def __init__(self, services):
        super().__init__(auth_svc=services['auth_svc'])
        self._api_manager = AdversaryApiManager(data_svc=services['data_svc'], file_svc=services['file_svc'])

    def add_routes(self, app: web.Application):
        router = app.router
        router.add_get('/adversaries', self.get_adversaries)
        router.add_get('/adversaries/{adversary_id}', self.get_adversary_by_id)
        router.add_post('/adversaries', self.create_adversary)
        router.add_patch('/adversaries/{adversary_id}', self.update_adversary)
        router.add_put('/adversaries/{adversary_id}', self.create_or_update_adversary)
        router.add_delete('/adversaries/{adversary_id}', self.delete_adversary)

    @aiohttp_apispec.docs(tags=['adversaries'])
    @aiohttp_apispec.querystring_schema(BaseGetAllQuerySchema)
    @aiohttp_apispec.response_schema(AdversarySchema(many=True, partial=True))
    async def get_adversaries(self, request: web.Request):
        sort = request['querystring'].get('sort', 'name')
        include = request['querystring'].get('include')
        exclude = request['querystring'].get('exclude')

        access = await self.get_request_permissions(request)

        adversaries = self._api_manager.find_and_dump_objects('adversaries', access, sort, include, exclude)
        return web.json_response(adversaries)

    @aiohttp_apispec.docs(tags=['adversaries'])
    @aiohttp_apispec.querystring_schema(BaseGetOneQuerySchema)
    @aiohttp_apispec.response_schema(AdversarySchema(partial=True))
    async def get_adversary_by_id(self, request: web.Request):
        adversary_id = request.match_info['adversary_id']
        include = request['querystring'].get('include')
        exclude = request['querystring'].get('exclude')

        access = await self.get_request_permissions(request)
        query = dict(adversary_id=adversary_id)
        search = {**query, **access}

        adversary = self._api_manager.find_and_dump_object('adversaries', search, include, exclude)
        if not adversary:
            raise JsonHttpNotFound(f'Adversary not found: {adversary_id}')

        return web.json_response(adversary)

    @aiohttp_apispec.docs(tags=['adversaries'])
    @aiohttp_apispec.request_schema(AdversarySchema)
    @aiohttp_apispec.response_schema(AdversarySchema)
    async def create_adversary(self, request: web.Request):
        adversary_data = await request.json()
        access = await self.get_request_permissions(request)

        adversary_id = adversary_data.get('adversary_id')
        if adversary_id:
            search = dict(adversary_id=adversary_id)
            search_adversary = next(self._api_manager.find_objects('adversaries', search), None)
            if search_adversary is not None:
                raise JsonHttpBadRequest(f'An adversary exists with the given id: {adversary_id}')

        adversary = await self._api_manager.create_adversary(adversary_data, access)
        return web.json_response(adversary.display)

    @aiohttp_apispec.docs(tags=['adversaries'])
    @aiohttp_apispec.request_schema(AdversarySchema(partial=True))
    @aiohttp_apispec.response_schema(AdversarySchema)
    async def update_adversary(self, request: web.Request):
        adversary_id = request.match_info['adversary_id']
        adversary_data = await request.json()
        adversary_data['adversary_id'] = adversary_id

        access = await self.get_request_permissions(request)
        query = dict(adversary_id=adversary_id)
        search = {**query, **access}

        adversary = await self._api_manager.update_adversary(adversary_data, search)
        if not adversary:
            raise JsonHttpNotFound(f'Adversary not found: {adversary_id}')

        return web.json_response(adversary.display)

    @aiohttp_apispec.docs(tags=['adversaries'])
    @aiohttp_apispec.request_schema(AdversarySchema(partial=True))
    @aiohttp_apispec.response_schema(AdversarySchema)
    async def create_or_update_adversary(self, request: web.Request):
        adversary_id = request.match_info['adversary_id']
        adversary_data = await request.json()
        adversary_data['adversary_id'] = adversary_id

        access = await self.get_request_permissions(request)
        search = dict(adversary_id=adversary_id)

        search_adversary = next(self._api_manager.find_objects('adversaries', search), None)
        if search_adversary is None:
            adversary = await self._api_manager.create_adversary(adversary_data, access)
        else:
            if search_adversary.access in access['access']:
                adversary = await self._api_manager.replace_adversary(search_adversary, adversary_data)
            else:
                raise JsonHttpForbidden(f'Cannot update adversary due to insufficient permissions: {adversary_id}')

        return web.json_response(adversary.display)

    @aiohttp_apispec.docs(tags=['adversaries'])
    @aiohttp_apispec.response_schema(AdversarySchema)
    async def delete_adversary(self, request: web.Request):
        adversary_id = request.match_info['adversary_id']

        access = await self.get_request_permissions(request)
        query = dict(adversary_id=adversary_id)
        search = {**query, **access}

        adversary = self._api_manager.find_and_dump_object('adversaries', search)
        if not adversary:
            raise JsonHttpNotFound(f'Adversary not found: {adversary_id}')

        await self._api_manager.remove_object_from_memory_by_id(ram_key='adversaries', id_value=adversary_id,
                                                                id_attribute='adversary_id')
        await self._api_manager.remove_object_from_disk_by_id(ram_key='adversaries', id_value=adversary_id)

        return web.HTTPNoContent()
