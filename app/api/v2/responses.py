import json

import marshmallow as ma
from aiohttp import web

from app.api.v2.schemas.error_schemas import JsonHttpErrorSchema


class JsonHttpErrorResponse:
    def __init__(self, error, details=None, **kwargs):
        kwargs['content_type'] = 'application/json'
        kwargs['text'] = JsonHttpErrorSchema.serialize(error, details)
        super().__init__(**kwargs)


class JsonHttpBadRequest(JsonHttpErrorResponse, web.HTTPBadRequest):
    """An HTTP 400 response with a json formatted body."""
    pass


class JsonHttpForbidden(JsonHttpErrorResponse, web.HTTPForbidden):
    """An HTTP 403 response with a json formatted body."""
    pass


@web.middleware
async def json_request_validation_middleware(request, handler):
    """Middleware that converts json decoding and marshmallow validation
    errors into 400 responses w/ json bodies.
    """
    try:
        return await handler(request)
    except ma.ValidationError as ex:
        # Note that this is only raised when loading via marshmallow, not serialization
        raise JsonHttpBadRequest('Received invalid json', details=ex.normalized_messages())
    except json.JSONDecodeError:
        raise JsonHttpBadRequest('Unexpected error occurred while parsing json')
