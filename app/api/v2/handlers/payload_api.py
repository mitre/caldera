import aiohttp_apispec
from aiohttp import web

from app.api.v2.handlers.base_object_api import BaseObjectApi
from app.api.v2.managers.base_api_manager import BaseApiManager
from app.api.v2.schemas.base_schemas import BaseGetAllQuerySchema, BaseGetOneQuerySchema


class PayloadApi(BaseApi):
    def __init__(self, services):
        super().__init__(auth_svc=services['auth_svc'])

    def add_routes(self, app: web.Application):
        router = app.router
        router.add_get('/payloads', self.get_obfuscators)

    @aiohttp_apispec.docs(tags=['payloads'],
                          summary='Retrieve payloads',
                          description='Retrieves all stored payloads.')
    @aiohttp_apispec.querystring_schema(BaseGetAllQuerySchema)
    @aiohttp_apispec.response_schema(PayloadSchema(many=True, partial=True),
                                     description='Returns a list of all payloads in PayloadSchema format.')
    async def get_obfuscators(self, request: web.Request):
        sources = await self.get_all_objects(request)
        return web.json_response(sources)
