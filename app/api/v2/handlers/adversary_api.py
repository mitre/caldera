import json

import aiohttp_apispec
from aiohttp import web

from app.api.v2.handlers.base_object_api import BaseObjectApi
from app.api.v2.managers.adversary_api_manager import AdversaryApiManager
from app.api.v2.schemas.base_schemas import BaseGetAllQuerySchema, BaseGetOneQuerySchema
from app.objects.c_adversary import Adversary, AdversarySchema


class AdversaryApi(BaseObjectApi):
    def __init__(self, services):
        super().__init__(description='adversary', obj_class=Adversary, schema=AdversarySchema, ram_key='adversaries',
                         id_property='adversary_id', auth_svc=services['auth_svc'])
        self._api_manager = AdversaryApiManager(data_svc=services['data_svc'], file_svc=services['file_svc'])

    def add_routes(self, app: web.Application):
        router = app.router
        adversaries_by_id_path = '/adversaries/{adversary_id}'
        router.add_get('/adversaries', self.get_adversaries)
        router.add_get(adversaries_by_id_path, self.get_adversary_by_id)
        router.add_post('/adversaries', self.create_adversary)
        router.add_patch(adversaries_by_id_path, self.update_adversary)
        router.add_put(adversaries_by_id_path, self.create_or_update_adversary)
        router.add_delete(adversaries_by_id_path, self.delete_adversary)

    @aiohttp_apispec.docs(tags=['adversaries'])
    @aiohttp_apispec.querystring_schema(BaseGetAllQuerySchema)
    @aiohttp_apispec.response_schema(AdversarySchema(many=True, partial=True))
    async def get_adversaries(self, request: web.Request):
        adversaries = await self.get_all_objects(request)
        return web.json_response(adversaries)

    @aiohttp_apispec.docs(tags=['adversaries'])
    @aiohttp_apispec.querystring_schema(BaseGetOneQuerySchema)
    @aiohttp_apispec.response_schema(AdversarySchema(partial=True))
    async def get_adversary_by_id(self, request: web.Request):
        adversary = await self.get_object(request)
        return web.json_response(adversary)

    @aiohttp_apispec.docs(tags=['adversaries'])
    @aiohttp_apispec.request_schema(AdversarySchema)
    @aiohttp_apispec.response_schema(AdversarySchema)
    async def create_adversary(self, request: web.Request):
        adversary = await self.create_on_disk_object(request)
        adversary = await self._api_manager.verify_adversary(adversary)
        return web.json_response(adversary.display)

    @aiohttp_apispec.docs(tags=['adversaries'])
    @aiohttp_apispec.request_schema(AdversarySchema(partial=True, exclude=['adversary_id']))
    @aiohttp_apispec.response_schema(AdversarySchema)
    async def update_adversary(self, request: web.Request):
        adversary = await self.update_on_disk_object(request)
        adversary = await self._api_manager.verify_adversary(adversary)
        return web.json_response(adversary.display)

    @aiohttp_apispec.docs(tags=['adversaries'])
    @aiohttp_apispec.request_schema(AdversarySchema(partial=True))
    @aiohttp_apispec.response_schema(AdversarySchema)
    async def create_or_update_adversary(self, request: web.Request):
        adversary = await self.create_or_update_on_disk_object(request)
        adversary = await self._api_manager.verify_adversary(adversary)
        return web.json_response(adversary.display)

    @aiohttp_apispec.docs(tags=['adversaries'])
    @aiohttp_apispec.response_schema(AdversarySchema)
    async def delete_adversary(self, request: web.Request):
        await self.delete_on_disk_object(request)
        return web.HTTPNoContent()

    async def create_on_disk_object(self, request: web.Request):
        data = await request.json()
        data.pop('id', None)
        await self._error_if_object_with_id_exists(data.get(self.id_property))
        access = await self.get_request_permissions(request)
        obj = await self._api_manager.create_on_disk_object(data, access, self.ram_key, self.id_property,
                                                            self.obj_class)
        return obj

    async def _parse_common_data_from_request(self, request) -> (dict, dict, str, dict, dict):
        data = {}
        raw_body = await request.read()
        if raw_body:
            data = json.loads(raw_body)
        data.pop('id', None)
        obj_id = request.match_info.get(self.id_property, '')
        if obj_id:
            data[self.id_property] = obj_id
        access = await self.get_request_permissions(request)
        query = {self.id_property: obj_id}
        search = {**query, **access}
        return data, access, obj_id, query, search
