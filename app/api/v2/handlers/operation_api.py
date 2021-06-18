import aiohttp_apispec
from aiohttp import web

from app.api.v2.handlers.base_object_api import BaseObjectApi
from app.api.v2.managers.base_api_manager import BaseApiManager
from app.api.v2.schemas.base_schemas import BaseGetAllQuerySchema, BaseGetOneQuerySchema
from app.objects.c_operation import Operation, OperationSchema


class OperationApi(BaseObjectApi):
    def __init__(self, services):
        super().__init__(description='operation', obj_class=Operation, schema=OperationSchema, ram_key='operations',
                         id_property='id', auth_svc=services['auth_svc'])
        self._api_manager = BaseApiManager(data_svc=services['data_svc'], file_svc=services['file_svc'])

    def add_routes(self, app: web.Application):
        router = app.router
        router.add_get('/operations', self.get_operations)
        router.add_get('/operations/{id}', self.get_operation_by_id)
        router.add_post('/operations', self.create_operation)
        router.add_put('/operations/{id}', self.create_or_update_operation)
        router.add_patch('/operations/{id}', self.update_operation)
        router.add_delete('/operations/{id}', self.delete_operation)

        router.add_get('/operations/{id}/report', self.get_operation_report)

        router.add_get('/operations/{id}/links', self.get_operation_links)
        router.add_get('/operations/{id}/links/{id}', self.get_operation_link)
        router.add_put('/operations/{id}/links/{id}', self.create_or_update_operation_link)

        router.add_post('/operations/{id}/potential-links', self.create_potential_links)
        router.add_get('/operations/{id}/potential-links', self.get_potential_links)
        router.add_get('/operations/{id}/potential-links/{paw}', self.get_potential_link)

    @aiohttp_apispec.docs(tags=['operations'])
    @aiohttp_apispec.querystring_schema(BaseGetAllQuerySchema)
    @aiohttp_apispec.response_schema(OperationSchema(many=True, partial=True))
    def get_operations(self, request: web.Request):
        operations = await self.get_all_objects(request)
        return web.json_response(operations)

    @aiohttp_apispec.docs(tags=['operations'])
    @aiohttp_apispec.querystring_schema(BaseGetOneQuerySchema)
    @aiohttp_apispec.response_schema(OperationSchema(partial=True))
    def get_operation_by_id(self, request: web.Request):
        operation = await self.get_object(request)
        return web.json_response(operation)

    @aiohttp_apispec.docs(tags=['operations'])
    @aiohttp_apispec.request_schema(OperationSchema)
    @aiohttp_apispec.response_schema(OperationSchema)
    def create_operation(self, request: web.Request):
        operation = await self.create_object(request)
        return web.json_response(operation.display)

    @aiohttp_apispec.docs(tags=['operations'])
    @aiohttp_apispec.request_schema(OperationSchema(partial=True))
    @aiohttp_apispec.response_schema(OperationSchema)
    def create_or_update_operation(self, request: web.Request):
        operation = await self.create_or_update_object(request)
        return web.json_response(operation.display)

    @aiohttp_apispec.docs(tags=['operations'])
    @aiohttp_apispec.request_schema(OperationSchema(partial=True))
    @aiohttp_apispec.response_schema(OperationSchema(partial=True))
    def update_operation(self, request: web.Request):
        operation = await self.update_object(request)
        return web.json_response(operation.display)

    @aiohttp_apispec.docs(tags=['operations'])
    @aiohttp_apispec.request_schema(OperationSchema)
    def delete_operation(self, request: web.Request):
        await self.delete_object(request)
        return web.HTTPNoContent()

    @aiohttp_apispec.docs(tags=['operations'])
    def get_operation_report(self, request: web.Request):
        pass

    @aiohttp_apispec.docs(tags=['operations'])
    def get_operation_links(self, request: web.Request):
        pass

    @aiohttp_apispec.docs(tags=['operations'])
    def get_operation_link(self, request: web.Request):
        pass

    @aiohttp_apispec.docs(tags=['operations'])
    def create_or_update_operation_link(self, request: web.Request):
        pass

    @aiohttp_apispec.docs(tags=['operations'])
    def create_potential_links(self, request: web.Request):
        pass

    @aiohttp_apispec.docs(tags=['operations'])
    def get_potential_links(self, request: web.Request):
        pass

    @aiohttp_apispec.docs(tags=['operations'])
    def get_potential_link(self, request: web.Request):
        pass
