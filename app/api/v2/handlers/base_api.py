import abc
import json
import logging

import marshmallow as ma
from aiohttp import web

from app.api.v2.errors import RequestUnparsableJsonError, RequestValidationError

DEFAULT_LOGGER_NAME = 'rest_api'


class BaseApi(abc.ABC):
    def __init__(self, auth_svc, logger=None):
        self._auth_svc = auth_svc
        self._log = logger or self._create_default_logger()

    @property
    def log(self):
        return self._log

    @abc.abstractmethod
    def add_routes(self, app: web.Application):
        raise NotImplementedError

    async def get_request_permissions(self, request: web.Request):
        return dict(access=tuple(await self._auth_svc.get_permissions(request)))

    @staticmethod
    async def parse_json_body(request: web.Request, schema: ma.Schema):
        try:
            parsed = schema.load(await request.json())
        except (TypeError, json.JSONDecodeError):
            raise RequestUnparsableJsonError
        except ma.ValidationError as ex:
            raise RequestValidationError(
                message='Request contains schema-invalid json',
                errors=ex.normalized_messages()
            )
        return parsed

    @staticmethod
    def _create_default_logger():
        return logging.getLogger(DEFAULT_LOGGER_NAME)
