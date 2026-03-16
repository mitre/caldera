import inspect
import functools
import types

from aiohttp import web
from aiohttp_session import get_session
from hmac import compare_digest
from aiohttp.web_exceptions import HTTPForbidden


def is_handler_authentication_exempt(handler):
    """Return True if the endpoint handler is authentication exempt."""
    try:
        if hasattr(handler, '__caldera_unauthenticated__'):
            is_unauthenticated = handler.__caldera_unauthenticated__
        else:
            is_unauthenticated = handler.keywords.get('handler').__caldera_unauthenticated__
    except AttributeError:
        is_unauthenticated = False
    return is_unauthenticated


def _wrap_async_method(method: types.MethodType):
    """Wrap the input bound async method in an async function."""
    async def wrapper(*args, **kwargs):
        return await method(*args, **kwargs)
    return functools.wraps(method)(wrapper)


def _wrap_sync_method(method: types.MethodType):
    """Wrap the input bound method in an async function."""
    def wrapper(*args, **kwargs):
        return method(*args, **kwargs)
    return functools.wraps(method)(wrapper)


def _wrap_method(method: types.MethodType):
    if inspect.iscoroutinefunction(method):
        return _wrap_async_method(method)
    return _wrap_sync_method(method)


def authentication_exempt(handler):
    """Mark the endpoint handler as not requiring authentication.

    Note:
        This only applies when the authentication_required_middleware is
        being used.
    """
    # Can't set attributes directly on a bound method so we need to
    # wrap it in a function that we can mark it as unauthenticated
    if inspect.ismethod(handler):
        handler = _wrap_method(handler)
    handler.__caldera_unauthenticated__ = True
    return handler


def authentication_required_middleware_factory(auth_svc):
    """Enforce authentication on every endpoint within an web application.

    Note:
        Any endpoint handler can opt-out of authentication using the
        @authentication_exempt decorator.
    """
    @web.middleware
    async def authentication_required_middleware(request, handler):
        if is_handler_authentication_exempt(handler):
            return await handler(request)
        if not await auth_svc.is_request_authenticated(request):
            raise web.HTTPUnauthorized()
        return await handler(request)
    return authentication_required_middleware


def csrf_protect_middleware_factory(auth_svc):
    """Protect unsafe (state-modifying) requests against CSRF for session-authenticated users.

    Behavior:
    - Allow safe methods (GET, HEAD, OPTIONS) without checks.
    - If request provides an API key (header KEY), skip CSRF checks.
    - For session-authenticated requests using unsafe methods, compare the X-CSRF-Token
      header to the token stored in the server-side session (recommended) and reject
      requests with missing/invalid tokens with HTTP 403.
    """
    @web.middleware
    async def csrf_protect_middleware(request, handler):
        # Skip safe methods
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return await handler(request)

        # If API key auth is present, skip CSRF checks
        if request.headers.get('KEY'):
            return await handler(request)

        # If the endpoint handler is explicitly decorated as authentication-exempt,
        # allow it to proceed without CSRF validation. This covers endpoints like
        # login which must be callable before a session and CSRF token exist.
        if is_handler_authentication_exempt(handler):
            return await handler(request)

        # For session-authenticated requests, validate token
        try:
            session = await get_session(request)
            token = session.get('csrf_token') if session is not None else None
            header = request.headers.get('X-CSRF-Token') or request.headers.get('X-XSRF-TOKEN')
            # check if there is a token, the header is missing, and whether the token and header
            # hash authentication works
            if not token or not header or not compare_digest(header, token):
                raise HTTPForbidden(text='Missing or invalid CSRF token')
        except HTTPForbidden:
            raise
        except Exception:
            # If something goes wrong accessing the session, deny the request
            raise HTTPForbidden(text='CSRF validation error')

        return await handler(request)

    return csrf_protect_middleware


@web.middleware
async def pass_option_middleware(request, handler):
    """Allow all 'OPTIONS' request to the server to return 200
    This mitigates CORS issues while developing the UI.
    """
    if request.method == 'OPTIONS':
        raise web.HTTPOk()
    return await handler(request)
