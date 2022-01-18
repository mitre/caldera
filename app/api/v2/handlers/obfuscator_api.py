import aiohttp_apispec
from aiohttp import web

from app.api.v2.handlers.base_object_api import BaseObjectApi
from app.api.v2.managers.base_api_manager import BaseApiManager
from app.api.v2.schemas.base_schemas import BaseGetAllQuerySchema, BaseGetOneQuerySchema
from app.objects.c_obfuscator import Obfuscator, ObfuscatorSchema


class ObfuscatorApi(BaseObjectApi):
    def __init__(self, services):
        super().__init__(description='obfuscator', obj_class=Obfuscator, schema=ObfuscatorSchema, ram_key='obfuscators',
                         id_property='name', auth_svc=services['auth_svc'])
        self._api_manager = BaseApiManager(data_svc=services['data_svc'], file_svc=services['file_svc'])

    def add_routes(self, app: web.Application):
        router = app.router
        router.add_get('/obfuscators', self.get_obfuscators)
        router.add_get('/obfuscators/{name}', self.get_obfuscator_by_name)

    @aiohttp_apispec.docs(tags=['obfuscators'],
                          summary='Retrieve obfuscators',
                          description='Retrieves all stored obfuscators.')
    @aiohttp_apispec.querystring_schema(BaseGetAllQuerySchema)
    @aiohttp_apispec.response_schema(ObfuscatorSchema(many=True, partial=True),
                                     description='Returns a list of all obfuscators in ObfuscatorSchema format.')
    async def get_obfuscators(self, request: web.Request):
        sources = await self.get_all_objects(request)
        return web.json_response(sources)

    @aiohttp_apispec.docs(tags=['obfuscators'],
                          summary='Retrieve an obfuscator by name',
                          description='Retrieve an obfuscator by name, as specified by {name} in the request url.',
                          parameters=[{
                              'in': 'path',
                              'name': 'name',
                              'schema': {'type': 'string'},
                              'required': 'true',
                              'description': 'Name of the Obfuscator'
                          }])
    @aiohttp_apispec.querystring_schema(BaseGetOneQuerySchema)
    @aiohttp_apispec.response_schema(ObfuscatorSchema(partial=True),
                                     description='Returns the specified obfuscator in ObfuscatorSchema format.')
    async def get_obfuscator_by_name(self, request: web.Request):
        source = await self.get_object(request)
        return web.json_response(source)
