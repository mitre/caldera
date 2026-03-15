import time
import pytest
from aiohttp import web
from unittest.mock import patch

from app.api.v2 import security
from app.service.auth_svc import AuthService, HEADER_API_KEY, CONFIG_API_KEY_RED, COOKIE_SESSION
from app.utility.base_world import BaseWorld


@pytest.fixture
def base_world():
    BaseWorld.clear_config()

    BaseWorld.apply_config(
        name='main',
        config={
            CONFIG_API_KEY_RED: 'abc123',

            'users': {
                'red': {'reduser': 'redpass'},
                'blue': {'blueuser': 'bluepass'}
            }
        }
    )

    yield BaseWorld
    BaseWorld.clear_config()


@pytest.fixture
def simple_webapp(event_loop, base_world):
    async def index(request):
        return web.Response(status=200, text='hello!')

    @security.authentication_exempt
    async def public(request):
        return web.Response(status=200, text='public')

    async def private(request):
        return web.Response(status=200, text='private')

    @security.authentication_exempt
    async def login(request):
        await auth_svc.login_user(request)  # Note: auth_svc defined in context function

    app = web.Application()
    app.router.add_get('/', index)
    app.router.add_post('/login', login)
    app.router.add_get('/public', public)
    app.router.add_get('/private', private)

    auth_svc = AuthService()

    event_loop.run_until_complete(
        auth_svc.apply(
            app=app,
            users=base_world.get_config('users')
        )
    )
    event_loop.run_until_complete(auth_svc.set_login_handlers(auth_svc.get_services()))

    # The authentication_required middleware needs to run after the session middleware.
    # AuthService.apply(...) adds session middleware to the app, so we can append the
    # the auth middleware after. Not doing this will cause a 500 in regards to the
    # session middleware not being set up correctly.
    app.middlewares.append(security.authentication_required_middleware_factory(auth_svc))

    return app


def test_function_is_authentication_exempt():
    def fake_handler(request):
        return None

    assert security.is_handler_authentication_exempt(fake_handler) is False
    assert security.is_handler_authentication_exempt(security.authentication_exempt(fake_handler)) is True


def test_unbound_method_is_authentication_exempt():
    class Api:
        @security.authentication_exempt
        def handler(self, request):
            return None

    api = Api()
    assert security.is_handler_authentication_exempt(api.handler)


def test_bound_method_is_authentication_exempt():
    class Api:
        def handler(self, request):
            return None

    api = Api()
    assert security.is_handler_authentication_exempt(api.handler) is False
    assert security.is_handler_authentication_exempt(security.authentication_exempt(api.handler)) is True


async def test_authentication_required_middleware_authenticated_endpoint_returns_401(simple_webapp, aiohttp_client):
    client = await aiohttp_client(simple_webapp)
    resp = await client.get('/private')
    assert resp.status == 401


async def test_authentication_required_middleware_exempt_endpoint(simple_webapp, aiohttp_client):
    client = await aiohttp_client(simple_webapp)
    resp = await client.get('/public')
    assert resp.status == 200


async def test_authentication_required_middleware_authenticated_endpoint_accepts_valid_api_key(simple_webapp, aiohttp_client):
    client = await aiohttp_client(simple_webapp)
    resp = await client.get('/private', headers={HEADER_API_KEY: 'abc123'})
    assert resp.status == 200


async def test_authentication_required_middleware_authenticated_endpoint_rejects_invalid_api_key(simple_webapp, aiohttp_client):
    client = await aiohttp_client(simple_webapp)
    resp = await client.get('/private', headers={HEADER_API_KEY: 'THIS WONT WORK'})
    assert resp.status == 401


async def test_authentication_required_middleware_authenticated_endpoint_accepts_session_cookie(simple_webapp, aiohttp_client):
    client = await aiohttp_client(simple_webapp)

    login_response = await client.post(
        '/login',
        data={'username': 'reduser', 'password': 'redpass'},
        allow_redirects=False  # I just didn't like that it followed the redirect for / and wanted the test to perform it manually.
    )

    assert login_response.status == 302
    assert COOKIE_SESSION in login_response.cookies

    # Internally the test client keeps track of the session and will forward any relavent cookies.
    index_response = await client.get('/private')
    assert index_response.status == 200


async def test_authentication_exempt_bound_method_returns_200(base_world, aiohttp_client):
    class Api:
        async def public(self, request):
            return web.Response(status=200, text='hello!')

    api = Api()
    app = web.Application()
    app.router.add_get('/public', security.authentication_exempt(api.public))

    auth_svc = AuthService()
    await auth_svc.apply(
        app=app,
        users=base_world.get_config('users')
    )

    app.middlewares.append(security.authentication_required_middleware_factory(auth_svc))

    client = await aiohttp_client(app)
    resp = await client.get('/public')
    assert resp.status == 200


# ---------------------------------------------------------------------------
# Rate limiting middleware tests
# ---------------------------------------------------------------------------

@pytest.fixture
def rate_limit_app():
    """Small aiohttp app with a very tight rate limit (3 req / 60 s)."""
    security._rate_limit_store.clear()

    async def index(request):
        return web.Response(status=200, text='ok')

    app = web.Application(middlewares=[security.rate_limit_middleware_factory(requests=3, window=60)])
    app.router.add_get('/', index)
    return app


@pytest.mark.anyio
async def test_rate_limit_requests_within_limit_are_allowed(rate_limit_app, aiohttp_client):
    client = await aiohttp_client(rate_limit_app)
    for _ in range(3):
        resp = await client.get('/')
        assert resp.status == 200


@pytest.mark.anyio
async def test_rate_limit_request_exceeding_limit_is_blocked(rate_limit_app, aiohttp_client):
    client = await aiohttp_client(rate_limit_app)
    for _ in range(3):
        await client.get('/')
    resp = await client.get('/')
    assert resp.status == 429


@pytest.mark.anyio
async def test_rate_limit_retry_after_header_present(rate_limit_app, aiohttp_client):
    client = await aiohttp_client(rate_limit_app)
    for _ in range(3):
        await client.get('/')
    resp = await client.get('/')
    assert resp.status == 429
    assert 'Retry-After' in resp.headers
    assert resp.headers['Retry-After'] == '60'


@pytest.mark.anyio
async def test_rate_limit_different_ips_have_independent_quotas(aiohttp_client):
    security._rate_limit_store.clear()

    async def index(request):
        return web.Response(status=200, text='ok')

    app = web.Application(middlewares=[security.rate_limit_middleware_factory(requests=3, window=60)])
    app.router.add_get('/', index)
    client = await aiohttp_client(app)

    # Exhaust quota for '1.1.1.1'
    for _ in range(3):
        await client.get('/', headers={'X-Forwarded-For': '1.1.1.1'})
    blocked = await client.get('/', headers={'X-Forwarded-For': '1.1.1.1'})
    assert blocked.status == 429

    # '2.2.2.2' should still be allowed
    allowed = await client.get('/', headers={'X-Forwarded-For': '2.2.2.2'})
    assert allowed.status == 200


@pytest.mark.anyio
async def test_rate_limit_x_forwarded_for_used_for_ip(aiohttp_client):
    security._rate_limit_store.clear()

    async def index(request):
        return web.Response(status=200, text='ok')

    app = web.Application(middlewares=[security.rate_limit_middleware_factory(requests=2, window=60)])
    app.router.add_get('/', index)
    client = await aiohttp_client(app)

    await client.get('/', headers={'X-Forwarded-For': '3.3.3.3'})
    await client.get('/', headers={'X-Forwarded-For': '3.3.3.3'})
    resp = await client.get('/', headers={'X-Forwarded-For': '3.3.3.3'})
    assert resp.status == 429


@pytest.mark.anyio
async def test_rate_limit_resets_after_window(aiohttp_client):
    security._rate_limit_store.clear()

    async def index(request):
        return web.Response(status=200, text='ok')

    app = web.Application(middlewares=[security.rate_limit_middleware_factory(requests=2, window=1)])
    app.router.add_get('/', index)
    client = await aiohttp_client(app)

    await client.get('/')
    await client.get('/')
    blocked = await client.get('/')
    assert blocked.status == 429

    # Advance time past the window by patching time.time
    with patch('app.api.v2.security.time') as mock_time:
        mock_time.time.return_value = time.time() + 2
        security._rate_limit_store.clear()
        resp = await client.get('/')
    assert resp.status == 200
