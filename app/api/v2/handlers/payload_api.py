import itertools
import pathlib

import aiohttp_apispec
from aiohttp import web
import marshmallow as ma

from app.api.v2.handlers.base_api import BaseApi
from app.api.v2.schemas.base_schemas import BaseGetAllQuerySchema


class PayloadSchema(ma.Schema):
    payloads = ma.fields.List(ma.fields.String())


class PayloadApi(BaseApi):
    def __init__(self, services):
        super().__init__(auth_svc=services['auth_svc'])
        self.data_svc = services['data_svc']
        self.file_svc = services['file_svc']

    def add_routes(self, app: web.Application):
        router = app.router
        router.add_get('/payloads', self.get_payloads)

    @aiohttp_apispec.docs(tags=['payloads'],
                          summary='Retrieve payloads',
                          description='Retrieves all stored payloads.')
    @aiohttp_apispec.querystring_schema(BaseGetAllQuerySchema)
    @aiohttp_apispec.response_schema(PayloadSchema(),
                                     description='Returns a list of all payloads in PayloadSchema format.')
    async def get_payloads(self, request: web.Request):
        cwd = pathlib.Path.cwd()
        payload_dirs = [cwd / 'data' / 'payloads']
        payload_dirs.extend(cwd / 'plugins' / plugin.name / 'payloads'
                            for plugin in await self.data_svc.locate('plugins') if plugin.enabled)
        payloads = {
            self.file_svc.remove_xored_extension(p.name)
            for p in itertools.chain.from_iterable(p_dir.glob('[!.]*') for p_dir in payload_dirs)
            if p.is_file()
        }

        return web.json_response(list(payloads))
