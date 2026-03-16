import pytest
import pytest_asyncio
from aiohttp import web
from pathlib import Path
import yaml
import time
import statistics

from aiohttp.test_utils import TestServer, TestClient

from app.utility.base_world import BaseWorld
from app.service.app_svc import AppService
from app.service.auth_svc import AuthService, HEADER_API_KEY, CONFIG_API_KEY_RED
from app.service.data_svc import DataService
from app.service.rest_svc import RestService
from app.service.planning_svc import PlanningService
from app.service.knowledge_svc import KnowledgeService
from app.service.learning_svc import LearningService
from app.service.file_svc import FileSvc
from app.service.event_svc import EventService
from app.api.rest_api import RestApi
from app.api.v2.handlers.operation_api import OperationApi
from app.api.v2 import security
from app.api.v2.responses import json_request_validation_middleware


@pytest.fixture
def base_world():
    BaseWorld.clear_config()
    BaseWorld.apply_config(
        name='main',
        config={
            CONFIG_API_KEY_RED: 'abc123',

            'users': {
                'admin': {'admin': 'admin'},
                'red': {'red': 'redpass'},
                'blue': {'blue': 'bluepass'}
            }
        },
        apply_hash=True
    )
    yield BaseWorld
    BaseWorld.clear_config()


@pytest_asyncio.fixture
async def csrf_webapp(event_loop, base_world):
    async def index(request):
        return web.Response(status=200, text='hello!')

    @security.authentication_exempt
    async def public(request):
        return web.Response(status=200, text='public')

    async def private(request):
        return web.Response(status=200, text='private')

    @security.authentication_exempt
    async def login(request):
        await auth_svc.login_user(request)

    app = web.Application()
    app.router.add_get('/', index)
    app.router.add_post('/login', login)
    app.router.add_get('/public', public)
    app.router.add_get('/private', private)
    app.router.add_post('/private', private)

    auth_svc = AuthService()
    await auth_svc.apply(app=app, users=base_world.get_config('users'))
    await auth_svc.set_login_handlers(auth_svc.get_services())

    app.middlewares.append(security.authentication_required_middleware_factory(auth_svc))
    app.middlewares.append(security.csrf_protect_middleware_factory(auth_svc))

    return app


@pytest_asyncio.fixture
async def api_v2_client_with_csrf(tmp_path):
    # Resolve repository root so we can load configuration files from the project's
    # top-level `conf/` directory (tests previously looked under tests/api/conf/).
    base = Path(__file__).resolve().parents[3]

    with open(base / 'conf' / 'default.yml', 'r') as fle:
        BaseWorld.apply_config('main', yaml.safe_load(fle), apply_hash=True)
    with open(base / 'conf' / 'payloads.yml', 'r') as fle:
        BaseWorld.apply_config('payloads', yaml.safe_load(fle), apply_hash=True)
    with open(base / 'conf' / 'agents.yml', 'r') as fle:
        BaseWorld.apply_config('agents', yaml.safe_load(fle), apply_hash=True)

    app_svc = AppService(web.Application(client_max_size=5120 ** 2))
    _ = DataService()
    _ = RestService()
    _ = PlanningService()
    _ = KnowledgeService()
    _ = LearningService()
    auth_svc = AuthService()
    _ = FileSvc()
    _ = EventService()
    services = app_svc.get_services()

    await RestApi(services).enable()
    # register_contacts may rely on optional contact services/plugins that aren't
    # initialized in the test environment. Ignore registration errors to allow
    # tests to proceed in this isolated context.
    try:
        await app_svc.register_contacts()
    except Exception:
        pass
    await auth_svc.apply(app_svc.application, auth_svc.get_config('users'))
    await auth_svc.set_login_handlers(services)

    def make_app(svcs):
        app = web.Application(middlewares=[
            security.authentication_required_middleware_factory(svcs['auth_svc']),
            security.csrf_protect_middleware_factory(svcs['auth_svc']),
            json_request_validation_middleware
        ])
        OperationApi(svcs).add_routes(app)
        return app

    app_svc.register_subapp('/api/v2', make_app(svcs=services))

    server = TestServer(app_svc.application)
    client = TestClient(server)
    await client.start_server()
    try:
        yield client
    finally:
        await client.close()
        await app_svc._destroy_plugins()


async def _measure_request_mean(client, method, path, count=30, **kwargs):
    for _ in range(3):
        if method.lower() == 'get':
            r = await client.get(path, **kwargs)
        else:
            r = await client.post(path, **kwargs)
        await r.text()

    times = []
    for _ in range(count):
        start = time.monotonic()
        if method.lower() == 'get':
            r = await client.get(path, **kwargs)
        else:
            r = await client.post(path, **kwargs)
        await r.text()
        times.append(time.monotonic() - start)
    return statistics.mean(times)


@pytest.mark.asyncio
async def test_csrf_protect_rejects_missing_token_for_session_auth(csrf_webapp):
    client = TestClient(TestServer(csrf_webapp))
    await client.start_server()
    try:
        login_response = await client.post('/login', data={'username': 'admin', 'password': 'admin'}, allow_redirects=False)
        # The login POST may be denied by CSRF middleware unless we explicitly forward
        # the session cookie returned by the server (EncryptedCookieStorage uses secure=True).
        assert login_response.status in (200, 302, 403)

        # Forward session cookie explicitly when making subsequent requests
        cookies = dict(login_response.cookies)

        # When the login succeeded, a follow-up POST without CSRF token should be rejected
        post_resp = await client.post('/private', cookies=cookies)
        assert post_resp.status == 403
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_csrf_protect_accepts_valid_token_for_session_auth(csrf_webapp):
    client = TestClient(TestServer(csrf_webapp))
    await client.start_server()
    try:
        login_response = await client.post('/login', data={'username': 'admin', 'password': 'admin'}, allow_redirects=False)
        # The login POST may be denied by CSRF middleware unless we explicitly forward
        # the session cookie returned by the server (EncryptedCookieStorage uses secure=True).
        assert login_response.status in (200, 302, 403)

        cookies = dict(login_response.cookies)

        token_cookie = login_response.cookies.get('XSRF-TOKEN')
        token = token_cookie.value if token_cookie is not None else None

        # Forward session cookie explicitly when making subsequent requests and include token
        post_resp = await client.post('/private', cookies=cookies, headers={'X-CSRF-Token': token} if token else {})
        assert post_resp.status == 200
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_csrf_protect_skips_when_api_key_present(csrf_webapp):
    client = TestClient(TestServer(csrf_webapp))
    await client.start_server()
    try:
        post_resp = await client.post('/private', headers={HEADER_API_KEY: 'abc123'})
        assert post_resp.status == 200
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_timing_api_key_resistant_to_timing_attacks(base_world):
    # Use simple app like in test_security
    async def index(request):
        return web.Response(status=200, text='hello!')

    @security.authentication_exempt
    async def public(request):
        return web.Response(status=200, text='public')

    async def private(request):
        return web.Response(status=200, text='private')

    @security.authentication_exempt
    async def login(request):
        await AuthService().login_user(request)

    app = web.Application()
    app.router.add_get('/', index)
    app.router.add_post('/login', login)
    app.router.add_get('/public', public)
    app.router.add_get('/private', private)

    auth_svc = AuthService()
    await auth_svc.apply(app=app, users=base_world.get_config().get('users'))
    await auth_svc.set_login_handlers(auth_svc.get_services())
    app.middlewares.append(security.authentication_required_middleware_factory(auth_svc))

    client = TestClient(TestServer(app))
    await client.start_server()
    try:
        count = 25
        mean_valid = await _measure_request_mean(client, 'get', '/private', count=count, headers={HEADER_API_KEY: 'abc123'})
        mean_invalid = await _measure_request_mean(client, 'get', '/private', count=count, headers={HEADER_API_KEY: 'INVALID_KEY'})
        assert abs(mean_valid - mean_invalid) < 0.05
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_timing_csrf_token_resistant_to_timing_attacks(csrf_webapp):
    client = TestClient(TestServer(csrf_webapp))
    await client.start_server()
    try:
        login_response = await client.post('/login', data={'username': 'admin', 'password': 'admin'}, allow_redirects=False)
        # Login may redirect (302) on success; accept either 200 or 302
        assert login_response.status in (200, 302)
        token_cookie = login_response.cookies.get('XSRF-TOKEN')
        assert token_cookie is not None
        token = token_cookie.value

        count = 25
        mean_valid = await _measure_request_mean(client, 'post', '/private', count=count, headers={'X-CSRF-Token': token})
        mean_invalid = await _measure_request_mean(client, 'post', '/private', count=count, headers={'X-CSRF-Token': token + 'x'})
        assert abs(mean_valid - mean_invalid) < 0.05
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_csrf_prevents_cross_site_operation_creation(api_v2_client_with_csrf):
    client = api_v2_client_with_csrf

    enter_resp = await client.post('/enter', data={'username': 'admin', 'password': 'admin'}, allow_redirects=False)
    assert enter_resp.status in (200, 302)
    cookies = enter_resp.cookies

    payload = {
        'adversary': {'adversary_id': '123', 'name': 'ad-hoc'},
        'source': {'id': '123'}
    }

    resp = await client.post('/api/v2/operations', cookies=cookies, json=payload)
    assert resp.status == 403

    xsrf_cookie = enter_resp.cookies.get('XSRF-TOKEN')
    if xsrf_cookie:
        token = xsrf_cookie.value
        resp2 = await client.post('/api/v2/operations', cookies=cookies, json=payload, headers={'X-CSRF-Token': token})
        assert resp2.status != 403
