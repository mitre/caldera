import aiohttp_apispec
from aiohttp import web

from app.api.v2.handlers.base_object_api import BaseObjectApi
from app.api.v2.managers.base_api_manager import BaseApiManager
from app.api.v2.schemas.base_schemas import BaseGetAllQuerySchema, BaseGetOneQuerySchema
from app.objects.c_source import Source, SourceSchema


class FactSourceApi(BaseObjectApi):
    def __init__(self, services):
        super().__init__(description='Fact Source', obj_class=Source, schema=SourceSchema, ram_key='sources',
                         id_property='id', auth_svc=services['auth_svc'])
        self._api_manager = BaseApiManager(data_svc=services['data_svc'], file_svc=services['file_svc'])

    def add_routes(self, app: web.Application):
        router = app.router
        router.add_get('/sources', self.get_fact_sources)
        router.add_get('/sources/{id}', self.get_fact_source_by_id)
        router.add_post('/sources', self.create_fact_source)
        router.add_patch('/sources/{id}', self.update_fact_source)
        router.add_put('/sources/{id}', self.create_or_update_source)
        router.add_delete('/sources/{id}', self.delete_source)

    @aiohttp_apispec.docs(tags=['sources'],
                          summary='Retrieve all Fact Sources.',
                          description='Returns a list of all Fact Sources, including custom-created ones.')
    @aiohttp_apispec.querystring_schema(BaseGetAllQuerySchema)
    @aiohttp_apispec.response_schema(SourceSchema(many=True, partial=True), description='Returns a list of all Sources dumped in SourceSchema format.')
    async def get_fact_sources(self, request: web.Request):
        sources = await self.get_all_objects(request)
        return web.json_response(sources)

    @aiohttp_apispec.docs(tags=['sources'],
                          summary='Retrieve a Fact Source by its id.',
                          description='Returns a Fact Source, given a source id.',
                          parameters=[{
                              'in': 'path',
                              'name': 'id',
                              'description': 'The id of the Fact Source',
                              'schema': {'type': 'string'},
                              'required': 'true'
                            }])
    @aiohttp_apispec.querystring_schema(BaseGetOneQuerySchema)
    @aiohttp_apispec.response_schema(SourceSchema(partial=True), description='Returns a single Source dumped in SourceSchema format.')
    async def get_fact_source_by_id(self, request: web.Request):
        source = await self.get_object(request)
        return web.json_response(source)

    @aiohttp_apispec.docs(tags=['sources'],
                          summary='Create a Fact Source.',
                          description='Create a new Fact Source using the format provided in the SourceSchema.')
    @aiohttp_apispec.docs(tags=['sources'])
    @aiohttp_apispec.request_schema(SourceSchema)
    @aiohttp_apispec.response_schema(SourceSchema, description='Returns a single Source dumped in SourceSchema format.')
    async def create_fact_source(self, request: web.Request):
        source = await self.create_on_disk_object(request)
        return web.json_response(source.display)

    @aiohttp_apispec.docs(tags=['sources'],
                          summary='Update an existing Fact Source.',
                          description='Returns an updated Fact Source. All fields in a Fact Source can be updated, except for "id" and "adjustments".',
                          parameters=[{
                            'in': 'path',
                            'name': 'id',
                            'description': 'The id of the Fact Source.',
                            'schema': {'type': 'string'},
                            'required': 'true'
                          }])
    @aiohttp_apispec.request_schema(SourceSchema(partial=True))
    @aiohttp_apispec.response_schema(SourceSchema, description='Returns a single Source dumped in SourceSchema format.')
    async def update_fact_source(self, request: web.Request):
        source = await self.update_on_disk_object(request)
        return web.json_response(source.display)

    @aiohttp_apispec.docs(tags=['sources'],
                          summary='Update an existing or create a new Fact Source.',
                          description='Use fields from the SourceSchema in the request body to replace an existing Fact Source or create a new Fact Source.',
                          parameters=[{
                            'in': 'path',
                            'name': 'id',
                            'description': 'The id of the Fact Source.',
                            'schema': {'type': 'string'},
                            'required': 'true'
                          }])
    @aiohttp_apispec.request_schema(SourceSchema(partial=True))
    @aiohttp_apispec.response_schema(SourceSchema, description='Returns a single Source dumped in SourceSchema format.')
    async def create_or_update_source(self, request: web.Request):
        source = await self.create_or_update_on_disk_object(request)
        return web.json_response(source.display)

    @aiohttp_apispec.docs(tags=['sources'],
                          summary='Delete an existing Fact Source.',
                          description='Delete a Fact Source, given its id.',
                          parameters=[{
                                'in': 'path',
                                'name': 'id',
                                'description': 'The id of the Fact Source to be deleted.',
                                'schema': {'type': 'string'},
                                'required': 'true'
                              }])
    @aiohttp_apispec.response_schema(SourceSchema, description='Returns DELETE status.')
    async def delete_source(self, request: web.Request):
        await self.delete_object(request)
        return web.HTTPNoContent()
