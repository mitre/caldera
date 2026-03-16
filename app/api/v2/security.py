import inspect
import functools
import time
import types
from collections import defaultdict, deque

from aiohttp import web


def rate_limit_middleware_factory(requests=360, window=60):
    """Return a sliding-window rate limiting middleware.

    Each call creates an independent per-IP request store so that multiple
    middleware instances (e.g. for different apps) do not interfere.

    Args:
        requests: Maximum number of requests allowed per window per IP.
        window: Window size in seconds.

    The middleware returns HTTP 429 Too Many Requests with a Retry-After
    header when the per-IP request count reaches the configured limit.

    .. warning::
        Client IP is read from the ``X-Forwarded-For`` header when present,
        falling back to ``request.remote``.  ``X-Forwarded-For`` should only
        be trusted when the server is behind a trusted reverse proxy;
        otherwise clients can spoof their IP to bypass rate limiting.
    """
    store = defaultdict(deque)

    @web.middleware
    async def rate_limit_middleware(request, handler):
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            client_ip = forwarded_for.split(',')[0].strip()
        else:
            client_ip = request.remote
        now = time.time()
        timestamps = store[client_ip]
        # Evict timestamps outside the sliding window
        while timestamps and timestamps[0] <= now - window:
            timestamps.popleft()
        # Prune empty entries to prevent unbounded memory growth
        if not timestamps and client_ip in store:
            del store[client_ip]
            timestamps = store[client_ip]
        if len(timestamps) >= requests:
            raise web.HTTPTooManyRequests(headers={'Retry-After': str(window)})
        timestamps.append(now)
        return await handler(request)

    # Expose the store for testing
    rate_limit_middleware._store = store
    return rate_limit_middleware


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


@web.middleware
async def pass_option_middleware(request, handler):
    """Allow all 'OPTIONS' request to the server to return 200
    This mitigates CORS issues while developing the UI.
    """
    if request.method == 'OPTIONS':
        raise web.HTTPOk()
    return await handler(request)
