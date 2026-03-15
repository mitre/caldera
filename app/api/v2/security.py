import inspect
import functools
import time
import types
from collections import defaultdict, deque

from aiohttp import web

# Per-IP sliding window request timestamp store.
# Keys are client IP strings; values are deques of monotonic timestamps.
_rate_limit_store = defaultdict(deque)


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


def rate_limit_middleware_factory(requests: int = 360, window: int = 60):
    """Return a sliding-window rate-limit middleware.

    Args:
        requests: Maximum number of requests allowed per *window* seconds per
                  client IP.  Defaults to 360 (6 req/s).
        window:   Time window in seconds.  Defaults to 60.

    Returns HTTP 429 with a ``Retry-After`` header when the limit is exceeded.
    Respects ``X-Forwarded-For`` so proxy deployments work correctly.
    """
    @web.middleware
    async def rate_limit_middleware(request, handler):
        forwarded_for = request.headers.get('X-Forwarded-For')
        client_ip = forwarded_for.split(',')[0].strip() if forwarded_for else (request.remote or 'unknown')

        now = time.monotonic()
        cutoff = now - window

        timestamps = _rate_limit_store[client_ip]
        while timestamps and timestamps[0] < cutoff:
            timestamps.popleft()

        if len(timestamps) >= requests:
            raise web.HTTPTooManyRequests(
                reason='Rate limit exceeded',
                headers={'Retry-After': str(window)},
            )

        timestamps.append(now)
        return await handler(request)

    return rate_limit_middleware


def docs_guard_middleware_factory(auth_svc):
    """Middleware that requires authentication for /api/docs and /static/swagger paths."""
    @web.middleware
    async def docs_guard_middleware(request, handler):
        if request.path.startswith('/api/docs') or request.path.startswith('/static/swagger'):
            if not auth_svc.request_has_valid_api_key(request):
                if not await auth_svc.request_has_valid_user_session(request):
                    raise web.HTTPUnauthorized(text='Authentication required for API documentation')
        return await handler(request)
    return docs_guard_middleware


@web.middleware
async def pass_option_middleware(request, handler):
    """Allow all 'OPTIONS' request to the server to return 200
    This mitigates CORS issues while developing the UI.
    """
    if request.method == 'OPTIONS':
        raise web.HTTPOk()
    return await handler(request)
