from aiohttp import web

from app.api.v2 import errors
from app.api.v2.schemas.error_schemas import JsonHttpErrorSchema


class JsonHttpErrorResponse:
    def __init__(self, error, details=None, **kwargs):
        kwargs['content_type'] = 'application/json'
        kwargs['text'] = JsonHttpErrorSchema.serialize(error, details)
        super().__init__(**kwargs)


class JsonHttpBadRequest(JsonHttpErrorResponse, web.HTTPBadRequest):
    """An HTTP 400 response with a json formatted body."""


class JsonHttpForbidden(JsonHttpErrorResponse, web.HTTPForbidden):
    """An HTTP 403 response with a json formatted body."""
    pass


class JsonHttpNotFound(JsonHttpErrorResponse, web.HTTPNotFound):
    """An HTTP 404 response with a json formatted body."""


@web.middleware
async def json_request_validation_middleware(request, handler):
    """Middleware that converts json decoding and marshmallow validation
    errors into 400 responses w/ json bodies.
    """
    try:
        return await handler(request)
    except errors.DataValidationError as ex:
        raise JsonHttpBadRequest(
            error=str(ex),
            details={ex.name: ex.value}
        )
    except errors.RequestValidationError as ex:
        raise JsonHttpBadRequest('Received invalid json', details=ex.errors)
    except errors.RequestUnparsableJsonError:
        raise JsonHttpBadRequest('Unexpected error occurred while parsing json')
