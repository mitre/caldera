import aiohttp_apispec
from aiohttp import web

from app.api.v2.handlers.base_api import BaseApi
from app.api.v2.managers.base_api_manager import BaseApiManager
from app.api.v2.responses import JsonHttpNotFound
from app.api.v2.schemas.base_schemas import BaseGetAllQuerySchema, BaseGetOneQuerySchema
from app.objects.c_source import SourceSchema


class FactSourceApi(BaseApi):
    def __init__(self, services):
        super().__init__(auth_svc=services['auth_svc'])
        self._api_manager = BaseApiManager(data_svc=services['data_svc'])

    def add_routes(self, app: web.Application):
        router = app.router
        router.add_get('/sources', self.get_fact_sources)
        router.add_get('/sources/{source_id}', self.get_fact_source_by_id)
        router.add_post('/sources', self.create_fact_source)

    @aiohttp_apispec.docs(tags=['sources'])
    @aiohttp_apispec.querystring_schema(BaseGetAllQuerySchema)
    @aiohttp_apispec.response_schema(SourceSchema(many=True))
    async def get_fact_sources(self, request: web.Request):
        sort = request['querystring'].get('sort', 'name')
        include = request['querystring'].get('include')
        exclude = request['querystring'].get('exclude')

        access = await self.get_request_permissions(request)

        sources = self._api_manager.get_objects_with_filters('sources', access, sort, include, exclude)
        return web.json_response(sources)

    @aiohttp_apispec.docs(tags=['sources'])
    @aiohttp_apispec.querystring_schema(BaseGetOneQuerySchema)
    @aiohttp_apispec.response_schema(SourceSchema)
    async def get_fact_source_by_id(self, request: web.Request):
        source_id = request.match_info['source_id']
        include = request['querystring'].get('include')
        exclude = request['querystring'].get('exclude')

        access = await self.get_request_permissions(request)
        query = dict(id=source_id)
        search = {**query, **access}

        source = self._api_manager.get_object_with_filters('sources', search, include, exclude)
        if not source:
            raise JsonHttpNotFound(f'Fact source not found: {source_id}')

        return web.json_response(source)

    @aiohttp_apispec.docs(tags=['sources'])
    @aiohttp_apispec.request_schema(SourceSchema)
    @aiohttp_apispec.response_schema(SourceSchema)
    async def create_fact_source(self, request: web.Request):
        source_data = await request.json()
        source = self._api_manager.store_json_as_schema(SourceSchema, source_data)
        return web.json_response(source.display)
