from aiohttp import web


def set_handler_authentication_exempt(handler):
    handler.__caldera_unauthenticated__ = True


def is_handler_authentication_exempt(handler):
    """Return True if the endpoint handler is authentication exempt."""
    try:
        is_unauthenticated = handler.__caldera_unauthenticated__
    except AttributeError:
        is_unauthenticated = False
    return is_unauthenticated


def authentication_exempt(handler):
    """Mark the endpoint handler as not requiring authentication.

    Note:
        This only applies when the authentication_required_middleware is
        being used.
    """
    set_handler_authentication_exempt(handler)
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
