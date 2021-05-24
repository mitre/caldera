import abc
import json
import logging

import marshmallow as ma
from aiohttp import web

from app.api.v2.errors import RequestUnparsableJsonError, RequestValidationError


DEFAULT_LOGGER_NAME = 'rest_api'


class BaseApi(abc.ABC):
    def __init__(self, logger=None):
        self._logger = logger or self._create_default_logger()

    @property
    def logger(self):
        return self._logger

    @abc.abstractmethod
    def add_routes(self, app: web.Application):
        pass

    async def parse_json_body(self, request: web.Request, schema: ma.Schema):
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

    def _create_default_logger(self):
        return logging.getLogger(DEFAULT_LOGGER_NAME)
