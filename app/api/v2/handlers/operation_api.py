import aiohttp_apispec

from aiohttp import web

from app.api.v2.handlers.base_object_api import BaseObjectApi
from app.api.v2.managers.operation_api_manager import OperationApiManager
from app.api.v2.responses import JsonHttpForbidden
from app.api.v2.schemas.base_schemas import BaseGetAllQuerySchema, BaseGetOneQuerySchema
from app.objects.c_operation import Operation, OperationSchema


class OperationApi(BaseObjectApi):
    def __init__(self, services):
        super().__init__(description='operation', obj_class=Operation, schema=OperationSchema, ram_key='operations',
                         id_property='id', auth_svc=services['auth_svc'])
        self._api_manager = OperationApiManager(services)

    def add_routes(self, app: web.Application):
        router = app.router
        router.add_get('/operations', self.get_operations)
        router.add_get('/operations/{id}', self.get_operation_by_id)
        router.add_post('/operations', self.create_operation)
        router.add_put('/operations/{id}', self.create_or_update_operation)
        router.add_patch('/operations/{id}', self.update_operation)
        router.add_delete('/operations/{id}', self.delete_operation)
        router.add_get('/operations/{id}/report', self.get_operation_report)

    @aiohttp_apispec.docs(tags=['operations'])
    @aiohttp_apispec.querystring_schema(BaseGetAllQuerySchema)
    @aiohttp_apispec.response_schema(OperationSchema(many=True, partial=True))
    async def get_operations(self, request: web.Request):
        operations = await self.get_all_objects(request)
        return web.json_response(operations)

    @aiohttp_apispec.docs(tags=['operations'])
    @aiohttp_apispec.querystring_schema(BaseGetOneQuerySchema)
    @aiohttp_apispec.response_schema(OperationSchema(partial=True))
    async def get_operation_by_id(self, request: web.Request):
        operation = await self.get_object(request)
        return web.json_response(operation)

    @aiohttp_apispec.docs(tags=['operations'])
    @aiohttp_apispec.request_schema(OperationSchema)
    @aiohttp_apispec.response_schema(OperationSchema)
    async def create_operation(self, request: web.Request):
        operation = await self.create_object(request)
        return web.json_response(operation.display)

    @aiohttp_apispec.docs(tags=['operations'])
    @aiohttp_apispec.request_schema(OperationSchema(partial=True))
    @aiohttp_apispec.response_schema(OperationSchema)
    async def create_or_update_operation(self, request: web.Request):
        operation = await self.create_or_update_object(request)
        return web.json_response(operation.display)

    @aiohttp_apispec.docs(tags=['operations'])
    @aiohttp_apispec.request_schema(OperationSchema(partial=True))
    @aiohttp_apispec.response_schema(OperationSchema(partial=True))
    async def update_operation(self, request: web.Request):
        operation = await self.update_object(request)
        return web.json_response(operation.display)

    @aiohttp_apispec.docs(tags=['operations'])
    @aiohttp_apispec.response_schema(OperationSchema)
    async def delete_operation(self, request: web.Request):
        await self.delete_object(request)
        return web.HTTPNoContent()

    @aiohttp_apispec.docs(tags=['operations'])
    @aiohttp_apispec.querystring_schema(BaseGetOneQuerySchema)
    async def get_operation_report(self, request: web.Request):
        operation_id = request.match_info.get('id')
        access = await self.get_request_permissions(request)
        report = await self._api_manager.get_operation_report(operation_id, access)
        return web.json_response(report)

    '''Helpers'''
    async def create_object(self, request: web.Request):
        data = await request.json()
        await self._error_if_object_with_id_exists(data.get(self.id_property))
        access = await self.get_request_permissions(request)
        return await self._api_manager.create_object_from_schema(self.schema, data, access)

    async def create_or_update_object(self, request: web.Request):
        data, access, obj_id, query, search = await self._parse_common_data_from_request(request)

        matched_obj = self._api_manager.find_object(self.ram_key, query)
        if matched_obj and matched_obj.access not in access['access']:
            raise JsonHttpForbidden(f'Cannot update {self.description} due to insufficient permissions: {obj_id}')
        return await self._api_manager.create_object_from_schema(self.schema, data, access, matched_obj)
