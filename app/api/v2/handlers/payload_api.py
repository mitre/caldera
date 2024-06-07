import asyncio
import itertools
import os
import pathlib
from io import IOBase

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

class PayloadCreateRequestSchema(schema.Schema):
    file = fields.Raw(type="file", required=True)

class PayloadDeleteRequestSchema(schema.Schema):
    name = fields.String(required=True)


class PayloadApi(BaseApi):
    def __init__(self, services):
        super().__init__(auth_svc=services['auth_svc'])
        self.data_svc = services['data_svc']
        self.file_svc = services['file_svc']

    def add_routes(self, app: web.Application):
        router = app.router
        router.add_get('/payloads', self.get_payloads)
        router.add_post("/payloads", self.post_payloads)
        router.add_delete("/payloads/{name}", self.delete_payloads)

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

    @aiohttp_apispec.docs(
        tags=['payloads'],
        summary='Create a payload',
        description='Uploads a payload.')
    @aiohttp_apispec.form_schema(PayloadCreateRequestSchema)
    @aiohttp_apispec.response_schema(
        PayloadSchema(),
        description="The created payload in a list in PayloadSchema format (with name changed in case of a duplicate).")
    async def post_payloads(self, request: web.Request):
        # As aiohttp_apispec.form_schema already calls request.multipart(),
        # accessing the file using the prefilled request["form"] dictionary.
        file_field: web.FileField = request["form"]["file"]

        file_name_candidate: str = file_field.filename
        file_path: str = os.path.join('data/payloads/', file_name_candidate)
        suffix: int = 1

        # Generating a file suffix in the case it already exists.
        while os.path.exists(file_path):
            file_name_candidate = f"{pathlib.Path(file_field.filename).stem}_" \
                                  f"{suffix}{pathlib.Path(file_field.filename).suffix}"
            file_path = os.path.join('data/payloads/', file_name_candidate)
            suffix += 1

        file_name: str = file_name_candidate

        # The file_field.file is of type IOBase: It uses blocking methods.
        # Putting blocking code into a dedicated method and thread...
        def save_file(target_file_path: str, io_base_src: IOBase):
            size: int = 0
            read_chunk: bool = True
            with open(target_file_path, 'wb') as buffered_io_base_dest:
                while read_chunk:
                    chunk: bytes = io_base_src.read(8192)
                    if chunk:
                        size += len(chunk)
                        buffered_io_base_dest.write(chunk)
                    else:
                        read_chunk = False

        loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
        await loop.run_in_executor(None, save_file, file_path, file_field.file)

        body: dict[list[str]] = {"payloads": [file_name]}
        return web.json_response(body)

    @aiohttp_apispec.docs(
        tags=['payloads'],
        summary='Delete a payload',
        description='Deletes a given payload.',
        responses = {
            204: {"description": "Payload has been properly deleted."},
            404: {"description": "Payload not found."},
        })
    @aiohttp_apispec.match_info_schema(PayloadDeleteRequestSchema)
    async def delete_payloads(self, request: web.Request):
        file_name: str = request.match_info.get("name")
        file_path: str = os.path.join('data/payloads/', file_name)

        response: web.HTTPException = None
        try:
            os.remove(file_path)
            response = web.HTTPNoContent()
        except FileNotFoundError:
            response = web.HTTPNotFound()
        return response
