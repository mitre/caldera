import itertools
import pathlib

import aiohttp_apispec
from aiohttp import web
from marshmallow import fields, schema

from app.api.v2.handlers.base_api import BaseApi


class PayloadQuerySchema(schema.Schema):
    sort = fields.Boolean(required=False, default=False)
    exclude_plugins = fields.Boolean(required=False, default=False)
    add_path = fields.Boolean(required=False, default=False)

class PayloadSchema(schema.Schema):
    payloads = fields.List(fields.String())


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
    @aiohttp_apispec.querystring_schema(PayloadQuerySchema)
    @aiohttp_apispec.response_schema(PayloadSchema(),
                                     description='Returns a list of all payloads in PayloadSchema format.')
    async def get_payloads(self, request: web.Request):
        sort: bool = request['querystring'].get('sort')
        exclude_plugins: bool = request['querystring'].get('exclude_plugins')
        add_path: bool = request['querystring'].get('add_path')

        cwd = pathlib.Path.cwd()
        payload_dirs = [cwd / 'data' / 'payloads']

        if not exclude_plugins:
            payload_dirs.extend(cwd / 'plugins' / plugin.name / 'payloads'
                                for plugin in await self.data_svc.locate('plugins') if plugin.enabled)

        payloads = {
            str(p.parent.relative_to(cwd) / self.file_svc.remove_xored_extension(p.name))
            if add_path
            else self.file_svc.remove_xored_extension(p.name)
            for p in itertools.chain.from_iterable(p_dir.glob('[!.]*') for p_dir in payload_dirs)
            if p.is_file()
        }

        payloads = list(payloads)
        if sort:
            payloads.sort()

        return web.json_response(payloads)
