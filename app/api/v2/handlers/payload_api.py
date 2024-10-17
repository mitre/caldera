import asyncio
import itertools
import os
import pathlib
from io import IOBase

import aiohttp_apispec
from aiohttp import web

from app.api.v2.handlers.base_api import BaseApi
from app.api.v2.schemas.payload_schemas import PayloadQuerySchema, PayloadSchema, PayloadCreateRequestSchema, \
    PayloadDeleteRequestSchema


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

        file_name, file_path = await self.__generate_file_name_and_path(file_field)

        # The file_field.file is of type IOBase: It uses blocking methods.
        # Putting blocking code into a dedicated method and thread...
        loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.__save_file, file_path, file_field.file)

        body: dict[list[str]] = {"payloads": [file_name]}
        return web.json_response(body)

    @aiohttp_apispec.docs(
        tags=['payloads'],
        summary='Delete a payload',
        description='Deletes a given payload.',
        responses={
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

    @classmethod
    async def __generate_file_name_and_path(cls, file_field: web.FileField) -> [str, str]:
        """
        Finds whether an uploaded file already exists in the payload directory.
        In the case, generates a new file name with an incremental suffix to avoid overriding the existing one.
        Otherwise, the original file name is used.

        :param file_field: The upload payload object.
        :return: A tuple containing the generated file name and path for future storage.
        """
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
        return file_name, file_path

    @staticmethod
    def __save_file(target_file_path: str, io_base_src: IOBase):
        """
        Save an uploaded file content into a targeted file path.
        Note this method calls blocking methods and must be run into a dedicated thread.

        :param target_file_path: The destination path to write to.
        :param io_base_src: The stream with file content to read from.
        """
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
