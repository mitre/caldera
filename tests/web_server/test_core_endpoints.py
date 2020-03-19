from http import HTTPStatus

# noinspection PyUnresolvedReferences
from tests.web_server.fixtures import *  # noqa F403, F401


async def test_home(aiohttp_client):
    resp = await aiohttp_client.get('/')
    assert resp.status == HTTPStatus.OK
    assert resp.content_type == 'text/html'


async def test_access_denied(aiohttp_client):
    resp = await aiohttp_client.get('/enter')
    assert resp.status == HTTPStatus.UNAUTHORIZED


async def test_login(aiohttp_client):
    resp = await aiohttp_client.post('/enter', allow_redirects=False, data=dict(username='admin', password='admin'))
    assert resp.status == HTTPStatus.FOUND
    assert resp.headers.get('Location') == '/'
    assert 'API_SESSION' in resp.cookies


async def test_core(aiohttp_client, authorized_cookies):
    resp = await aiohttp_client.post('/api/rest', json=dict(index='agents'), cookies=authorized_cookies)
    assert resp.status == HTTPStatus.OK
