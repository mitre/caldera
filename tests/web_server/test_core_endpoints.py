import os
from http import HTTPStatus
from pathlib import Path

import pytest
import yaml
from aiohttp import web

from app.api.rest_api import RestApi
from app.service.app_svc import AppService
from app.service.auth_svc import AuthService
from app.service.contact_svc import ContactService
from app.service.data_svc import DataService
from app.service.file_svc import FileSvc
from app.service.learning_svc import LearningService
from app.service.planning_svc import PlanningService
from app.service.rest_svc import RestService
from app.utility.base_world import BaseWorld


@pytest.fixture
def aiohttp_client(loop, aiohttp_client):

    async def initialize():
        with open(Path(__file__).parents[2] / 'conf' / 'default.yml', 'r') as fle:
            BaseWorld.apply_config('default', yaml.safe_load(fle))

        app_svc = AppService(web.Application())
        _ = DataService()
        _ = RestService()
        _ = PlanningService()
        _ = LearningService()
        auth_svc = AuthService()
        _ = ContactService()
        _ = FileSvc()
        services = app_svc.get_services()
        os.chdir(str(Path(__file__).parents[2]))

        await app_svc.register_contacts()
        await app_svc.load_plugins()
        _ = await RestApi(services).enable()
        await auth_svc.apply(app_svc.application, auth_svc.get_config('users'))
        return app_svc.application

    app = loop.run_until_complete(initialize())
    return loop.run_until_complete(aiohttp_client(app))


@pytest.fixture
def authorized_cookies(loop, aiohttp_client):
    async def get_cookie():
        r = await aiohttp_client.post('/enter', allow_redirects=False, data=dict(username='admin', password='admin'))
        return r.cookies
    return loop.run_until_complete(get_cookie())


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
