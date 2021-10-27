import json
import aiohttp_apispec

from aiohttp import web

from app.api.v2.handlers.base_object_api import BaseObjectApi
from app.api.v2.managers.operation_api_manager import OperationApiManager
from app.api.v2.responses import JsonHttpNotFound
from app.api.v2.schemas.base_schemas import BaseGetAllQuerySchema, BaseGetOneQuerySchema
from app.objects.c_operation import Operation, OperationSchema, OperationOutputRequestSchema
from app.objects.secondclass.c_link import LinkSchema


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
        router.add_patch('/operations/{id}', self.update_operation)
        router.add_delete('/operations/{id}', self.delete_operation)
        router.add_post('/operations/{id}/report', self.get_operation_report)
        router.add_post('/operations/{id}/event-logs', self.get_operation_event_logs)
        router.add_get('/operations/{id}/links', self.get_operation_links)
        router.add_get('/operations/{id}/links/{link_id}', self.get_operation_link)
        router.add_get('/operations/{id}/links/{link_id}/result', self.get_operation_link_result)
        router.add_patch('/operations/{id}/links/{link_id}', self.update_operation_link)
        router.add_post('/operations/{id}/potential-links', self.create_potential_link)
        router.add_get('/operations/{id}/potential-links', self.get_potential_links)
        router.add_get('/operations/{id}/potential-links/{paw}', self.get_potential_links_by_paw)

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

    @aiohttp_apispec.docs(tags=['operations'],
                          summary='Required nested schema fields are as follows: "adversary.adversary_id", '
                                  '"planner.planner_id", and "source.id".')
    @aiohttp_apispec.request_schema(OperationSchema())
    @aiohttp_apispec.response_schema(OperationSchema)
    async def create_operation(self, request: web.Request):
        operation = await self.create_object(request)
        return web.json_response(operation.display)

    @aiohttp_apispec.docs(tags=['operations'])
    @aiohttp_apispec.request_schema(OperationSchema(partial=True, only=['state',
                                                                        'autonomous',
                                                                        'obfuscator']))
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
    @aiohttp_apispec.request_schema(OperationOutputRequestSchema)
    async def get_operation_report(self, request: web.Request):
        operation_id = request.match_info.get('id')
        access = await self.get_request_permissions(request)
        output = await self._read_output_parameter_(request)
        report = await self._api_manager.get_operation_report(operation_id, access, output)
        return web.json_response(report)

    @aiohttp_apispec.docs(tags=['operations'])
    @aiohttp_apispec.querystring_schema(BaseGetOneQuerySchema)
    @aiohttp_apispec.request_schema(OperationOutputRequestSchema)
    async def get_operation_event_logs(self, request: web.Request):
        operation_id = request.match_info.get('id')
        access = await self.get_request_permissions(request)
        output = await self._read_output_parameter_(request)
        report = await self._api_manager.get_operation_event_logs(operation_id, access, output)
        return web.json_response(report)

    @aiohttp_apispec.docs(tags=['operations'])
    @aiohttp_apispec.querystring_schema(BaseGetAllQuerySchema)
    @aiohttp_apispec.response_schema(LinkSchema(many=True, partial=True))
    async def get_operation_links(self, request: web.Request):
        operation_id = request.match_info.get('id')
        access = await self.get_request_permissions(request)
        links = await self._api_manager.get_operation_links(operation_id, access)
        return web.json_response(links)

    @aiohttp_apispec.docs(tags=['operations'])
    @aiohttp_apispec.querystring_schema(BaseGetOneQuerySchema)
    @aiohttp_apispec.response_schema(LinkSchema(partial=True))
    async def get_operation_link(self, request: web.Request):
        operation_id = request.match_info.get('id')
        link_id = request.match_info.get('link_id')
        access = await self.get_request_permissions(request)
        link = await self._api_manager.get_operation_link(operation_id, link_id, access)
        return web.json_response(link)

    @aiohttp_apispec.docs(tags=['operations'])
    @aiohttp_apispec.querystring_schema(BaseGetOneQuerySchema)
    @aiohttp_apispec.response_schema(LinkSchema(partial=True))
    async def get_operation_link_result(self, request: web.Request):
        operation_id = request.match_info.get('id')
        link_id = request.match_info.get('link_id')
        access = await self.get_request_permissions(request)
        result = await self._api_manager.get_operation_link_result(operation_id, link_id, access)
        return web.json_response(result)

    @aiohttp_apispec.docs(tags=['operations'])
    @aiohttp_apispec.request_schema(LinkSchema(partial=True, only=['command', 'status']))
    @aiohttp_apispec.response_schema(LinkSchema)
    async def update_operation_link(self, request: web.Request):
        operation_id = request.match_info.get('id')
        link_id = request.match_info.get('link_id')
        access = await self.get_request_permissions(request)
        data = await request.json()
        link = await self._api_manager.update_operation_link(operation_id, link_id, data, access)
        return web.json_response(link)

    @aiohttp_apispec.docs(tags=['operations'], summary='The only required fields for this endpoint are "paw", '
                                                       '"executor.name", "executor.command", and "executor.platform". '
                                                       '"executor.command" is expected to be unencoded.')
    @aiohttp_apispec.request_schema(LinkSchema)
    @aiohttp_apispec.response_schema(LinkSchema)
    async def create_potential_link(self, request: web.Request):
        operation_id = request.match_info.get('id')
        access = await self.get_request_permissions(request)
        data = await request.json()
        potential_link = await self._api_manager.create_potential_link(operation_id, data, access)
        return web.json_response(potential_link)

    @aiohttp_apispec.docs(tags=['operations'])
    @aiohttp_apispec.querystring_schema(BaseGetAllQuerySchema)
    @aiohttp_apispec.response_schema(LinkSchema(many=True, partial=True))
    async def get_potential_links(self, request: web.Request):
        operation_id = request.match_info.get('id')
        access = await self.get_request_permissions(request)
        potential_links = await self._api_manager.get_potential_links(operation_id, access)
        return web.json_response(potential_links)

    @aiohttp_apispec.docs(tags=['operations'])
    @aiohttp_apispec.querystring_schema(BaseGetOneQuerySchema)
    @aiohttp_apispec.response_schema(LinkSchema(partial=True))
    async def get_potential_links_by_paw(self, request: web.Request):
        operation_id = request.match_info.get('id')
        paw = request.match_info.get('paw')
        access = await self.get_request_permissions(request)
        potential_links = await self._api_manager.get_potential_links(operation_id, access, paw)
        return web.json_response(potential_links)

    '''Overridden Methods'''

    async def create_object(self, request: web.Request):
        data = await request.json()
        await self._error_if_object_with_id_exists(data.get(self.id_property))
        access = await self.get_request_permissions(request)
        return await self._api_manager.create_object_from_schema(self.schema, data, access)

    async def update_object(self, request: web.Request):
        data, access, obj_id, query, search = await self._parse_common_data_from_request(request)
        obj = await self._api_manager.find_and_update_object(self.ram_key, data, search)
        if not obj:
            raise JsonHttpNotFound(f'{self.description.capitalize()} not found: {obj_id}')
        return obj

    ''' PRIVATE '''

    async def _read_output_parameter_(self, request: web.Request):
        raw_body = await request.read()
        output = False
        if raw_body:
            output = json.loads(raw_body).get('enable_agent_output', False)
        return output
