import pytest
from aiohttp import web
from pathlib import Path
import yaml
from aiohttp import web

from app.utility.base_world import BaseWorld
from app.service.app_svc import AppService
from app.service.auth_svc import AuthService
from app.service.data_svc import DataService
from app.service.rest_svc import RestService
from app.service.planning_svc import PlanningService
from app.service.knowledge_svc import KnowledgeService
from app.service.learning_svc import LearningService
from app.service.file_svc import FileSvc
from app.service.event_svc import EventService
from app.api.rest_api import RestApi
from app.api.v2.handlers.operation_api import OperationApi
from app.api.v2.security import csrf_protect_middleware_factory, authentication_required_middleware_factory
from app.api.v2.responses import json_request_validation_middleware


@pytest.fixture
async def api_v2_client_with_csrf(aiohttp_client, tmp_path):
    # Build app similar to conftest.api_v2_client but ensure CSRF middleware is added to the /api/v2 subapp
    base = Path(__file__).parents[1]

    # Load configs used by the app
    with open(base / 'conf' / 'default.yml', 'r') as fle:
        BaseWorld.apply_config('main', yaml.safe_load(fle))
    with open(base / 'conf' / 'payloads.yml', 'r') as fle:
        BaseWorld.apply_config('payloads', yaml.safe_load(fle))
    with open(base / 'conf' / 'agents.yml', 'r') as fle:
        BaseWorld.apply_config('agents', yaml.safe_load(fle))

    app_svc = AppService(web.Application(client_max_size=5120 ** 2))
    # Initialize core services used by RestApi and the v2 APIs
    _ = DataService()
    _ = RestService()
    _ = PlanningService()
    _ = KnowledgeService()
    _ = LearningService()
    auth_svc = AuthService()
    _ = FileSvc()
    _ = EventService()
    services = app_svc.get_services()

    # Enable REST endpoints (this registers the /enter login endpoint used to obtain cookies)
    _ = await RestApi(services).enable()
    await app_svc.register_contacts()
    await auth_svc.apply(app_svc.application, auth_svc.get_config('users'))
    await auth_svc.set_login_handlers(services)

    # Create the v2 subapp with CSRF protection middleware included
    def make_app(svcs):
        app = web.Application(middlewares=[
            authentication_required_middleware_factory(svcs['auth_svc']),
            csrf_protect_middleware_factory(svcs['auth_svc']),
            json_request_validation_middleware
        ])
        OperationApi(svcs).add_routes(app)
        return app

    app_svc.register_subapp('/api/v2', make_app(svcs=services))

    client = await aiohttp_client(app_svc.application)
    yield client
    await app_svc._destroy_plugins()


async def test_csrf_protect_rejects_missing_token_for_session_auth(csrf_webapp, aiohttp_client):
    """A session-authenticated POST without a valid CSRF header should be rejected with 403."""
    client = await aiohttp_client(csrf_webapp)

    login_response = await client.post(
        '/login',
        data={'username': 'admin', 'password': 'admin'},
        allow_redirects=False
    )

    assert login_response.status == 200
    assert COOKIE_SESSION in login_response.cookies

    post_resp = await client.post('/private')
    assert post_resp.status == 403


async def test_csrf_protect_accepts_valid_token_for_session_auth(csrf_webapp, aiohttp_client):
    """A session-authenticated POST with a valid CSRF header should be allowed."""
    client = await aiohttp_client(csrf_webapp)

    login_response = await client.post(
        '/login',
        data={'username': 'admin', 'password': 'admin'},
        allow_redirects=False
    )

    assert login_response.status == 200
    # The login handler exposes the CSRF token as a readable cookie named 'XSRF-TOKEN'
    token_cookie = login_response.cookies.get('XSRF-TOKEN')
    assert token_cookie is not None
    token = token_cookie.value

    post_resp = await client.post('/private', headers={'X-CSRF-Token': token})
    assert post_resp.status == 200


async def test_csrf_protect_skips_when_api_key_present(csrf_webapp, aiohttp_client):
    """If an API key header is present, CSRF checks should be skipped."""
    client = await aiohttp_client(csrf_webapp)

    post_resp = await client.post('/private', headers={HEADER_API_KEY: 'abc123'})
    assert post_resp.status == 200


# Timing-attack resistance tests
async def _measure_request_mean(client, method, path, count=30, **kwargs):
    # Warmup
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


async def test_timing_api_key_resistant_to_timing_attacks(simple_webapp, aiohttp_client):
    """Ensure API key validation does not leak timing differences between valid and invalid keys."""
    client = await aiohttp_client(simple_webapp)

    count = 25
    mean_valid = await _measure_request_mean(client, 'get', '/private', count=count, headers={HEADER_API_KEY: 'abc123'})
    mean_invalid = await _measure_request_mean(client, 'get', '/private', count=count, headers={HEADER_API_KEY: 'INVALID_KEY'})

    # Allow a small tolerance for network/test harness jitter (50ms)
    assert abs(mean_valid - mean_invalid) < 0.05


async def test_timing_csrf_token_resistant_to_timing_attacks(csrf_webapp, aiohttp_client):
    """Ensure CSRF token comparison does not leak timing differences between valid and invalid tokens."""
    client = await aiohttp_client(csrf_webapp)

    # Login to establish session and get token
    login_response = await client.post('/login', data={'username': 'admin', 'password': 'admin'}, allow_redirects=False)
    assert login_response.status == 200
    token_cookie = login_response.cookies.get('XSRF-TOKEN')
    assert token_cookie is not None
    token = token_cookie.value

    count = 25
    mean_valid = await _measure_request_mean(client, 'post', '/private', count=count, headers={'X-CSRF-Token': token})
    mean_invalid = await _measure_request_mean(client, 'post', '/private', count=count, headers={'X-CSRF-Token': token + 'x'})

    # Allow a small tolerance for network/test harness jitter (50ms)
    assert abs(mean_valid - mean_invalid) < 0.05

async def test_csrf_prevents_cross_site_operation_creation(api_v2_client_with_csrf):
    """Simulate an attacker-controlled page submitting a POST that will include the user's session cookie
    but will not be able to provide the X-CSRF-Token header. The CSRF middleware should block the request.
    """
    client = api_v2_client_with_csrf

    # Perform login on the main app to obtain authenticated session cookies
    enter_resp = await client.post('/enter', data={'username': 'admin', 'password': 'admin'}, allow_redirects=False)
    assert enter_resp.status in (200, 302)
    cookies = enter_resp.cookies

    # Attempt to create an operation without providing the X-CSRF-Token header.
    # This simulates a cross-site form POST originating from an attacker's page.
    payload = {
        'adversary': {'adversary_id': '123', 'name': 'ad-hoc'},
        'source': {'id': '123'}
    }

    resp = await client.post('/api/v2/operations', cookies=cookies, json=payload)
    # CSRF protection should reject this because no X-CSRF-Token header was supplied
    assert resp.status == 403

    # For completeness: if the client includes the legitimate X-CSRF-Token header (as same-origin scripts would),
    # the request should be allowed (happy-path). The login response sets an XSRF-TOKEN readable cookie; include it.
    xsrf_cookie = enter_resp.cookies.get('XSRF-TOKEN')
    if xsrf_cookie:
        token = xsrf_cookie.value
        resp2 = await client.post('/api/v2/operations', cookies=cookies, json=payload, headers={'X-CSRF-Token': token})
        # Depending on DB state and required payload, this may be accepted or rejected by business validation; it must not be CSRF 403.
        assert resp2.status != 403
