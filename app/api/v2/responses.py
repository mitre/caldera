from aiohttp import web
from json import JSONDecodeError
from marshmallow.exceptions import ValidationError

from app.api.v2 import errors
from app.api.v2.schemas.error_schemas import JsonHttpErrorSchema


class JsonHttpErrorResponse:
    """Base class for json formatted versions of aiohttp responses."""

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
async def apispec_request_validation_middleware(request, handler):
    """Middleware to handle errors thrown by schema validation

    Must be added before `validation_middleware`"""
    try:
        return await handler(request)
    except TypeError as ex:
        # ex: Schema `post_load()` instantiates an object, but required
        #   argument is missing
        raise JsonHttpBadRequest(
            error='Error parsing JSON',
            details=str(ex)
        )
    except AttributeError as ex:
        # ex: JSON contains attribute that does not exist in Schema
        # Or any other AttributeError...
        raise JsonHttpBadRequest(
            error='AttributeError',
            details=str(ex)
        )
    except ValidationError as ex:
        # ex: List of objects sent when single object expected
        raise JsonHttpBadRequest(
            error='Error parsing JSON: Could not validate Schema',
            details=str(ex)
        )
    except JSONDecodeError as ex:
        raise JsonHttpBadRequest(
            error='Unexpected error occurred while parsing json',
            details=str(ex)
        )


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
