import json

import marshmallow as ma
from aiohttp import web


class JsonHttpResponse:
    def __init__(self, errors, **kwargs):
        errors = [errors] if isinstance(errors, (str, bytes)) else errors
        kwargs['content_type'] = 'application/json'
        kwargs['text'] = json.dumps({'errors': errors})
        super().__init__(**kwargs)


class JsonHttpBadRequest(JsonHttpResponse, web.HTTPBadRequest):
    """An HTTP 400 response with a json formatted body."""
    pass


class JsonHttpForbidden(JsonHttpResponse, web.HTTPForbidden):
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
        raise JsonHttpBadRequest(ex.messages)
    except json.JSONDecodeError as ex:
        raise JsonHttpBadRequest(f'Received invalid json {ex}')
