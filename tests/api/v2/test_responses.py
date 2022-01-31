import pytest
from aiohttp import web


from app.api.v2 import errors, responses
from app.utility.base_world import BaseWorld


@pytest.fixture
def base_world():
    BaseWorld.clear_config()

    BaseWorld.apply_config(
        name='main',
        config={
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
    async def raise_validation_error(request):
        raise errors.RequestValidationError(
            errors={
                'foo': 'invalid type',
                'bar': 'invalid value'
            }
        )

    async def raise_request_unparsable_json_error(request):
        raise errors.RequestUnparsableJsonError

    async def success(request):
        return web.Response(status=200, text='OK')

    app = web.Application(
        middlewares=[
            responses.json_request_validation_middleware
        ]
    )

    app.router.add_get('/validation-error', raise_validation_error)
    app.router.add_get('/unparsable-json-error', raise_request_unparsable_json_error)
    app.router.add_get('/success', success)

    return app


async def test_middleware_passes_with_no_error(simple_webapp, aiohttp_client):
    client = await aiohttp_client(simple_webapp)
    resp = await client.get('/success')
    assert resp.status == 200


async def test_middleware_transforms_marshmallow_validation_error(simple_webapp, aiohttp_client):
    client = await aiohttp_client(simple_webapp)
    resp = await client.get('/validation-error')
    assert resp.status == 400

    json_body = await resp.json()
    expected_keys = ['error', 'details']

    for key in expected_keys:
        assert key in json_body


async def test_middleware_transforms_json_decode_error(simple_webapp, aiohttp_client):
    client = await aiohttp_client(simple_webapp)
    resp = await client.get('/unparsable-json-error')
    assert resp.status == 400

    json_body = await resp.json()
    assert 'error' in json_body
