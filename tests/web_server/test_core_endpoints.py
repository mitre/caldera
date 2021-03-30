import os
from http import HTTPStatus
from pathlib import Path

import pytest
import yaml
from aiohttp import web

from app.api.rest_api import RestApi
from app.objects.c_agent import Agent
from app.service.app_svc import AppService
from app.service.auth_svc import AuthService
from app.service.contact_svc import ContactService
from app.service.data_svc import DataService
from app.service.file_svc import FileSvc
from app.service.learning_svc import LearningService
from app.service.planning_svc import PlanningService
from app.service.rest_svc import RestService
from app.utility.base_service import BaseService
from app.utility.base_world import BaseWorld


@pytest.fixture
def aiohttp_client(loop, aiohttp_client):

    async def initialize():
        with open(Path(__file__).parents[2] / 'conf' / 'default.yml', 'r') as fle:
            BaseWorld.apply_config('main', yaml.safe_load(fle))
        with open(Path(__file__).parents[2] / 'conf' / 'payloads.yml', 'r') as fle:
            BaseWorld.apply_config('payloads', yaml.safe_load(fle))

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
        await app_svc.load_plugins(['sandcat', 'ssl'])
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


@pytest.fixture
def sample_agent(loop, aiohttp_client):
    kwargs = dict(architecture='amd64', exe_name='sandcat.go', executors=['shellcode_amd64', 'sh'],
                  group='red', host='testsystem.localdomain', location='./sandcat.go', pid=125266,
                  platform='linux', ppid=124042, privilege='User', server='http://127.0.0.1:8888',
                  username='testuser', paw=None, contact='http')

    agent = loop.run_until_complete(
        BaseService.get_service('data_svc').store(Agent(sleep_min=0, sleep_max=60, watchdog=0, **kwargs))
    )
    yield agent

    loop.run_until_complete(
        BaseService.get_service('data_svc').remove('agent', dict(paw=agent.paw))
    )


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


async def test_read_agent(aiohttp_client, authorized_cookies, sample_agent):
    resp = await aiohttp_client.post('/api/rest', json=dict(index='agents'), cookies=authorized_cookies)
    assert resp.status == HTTPStatus.OK
    agent_list = await resp.json()
    assert len(list(filter(lambda x: x['paw'] == sample_agent.paw, agent_list)))


async def test_modify_agent(aiohttp_client, authorized_cookies, sample_agent):
    resp = await aiohttp_client.put('/api/rest', json=dict(index='agents', paw=sample_agent.paw,
                                                           sleep_min=1, sleep_max=5), cookies=authorized_cookies)
    assert resp.status == HTTPStatus.OK
    agent_dict = await resp.json()
    assert agent_dict['sleep_max'] == 5
    assert sample_agent.sleep_min == 1
    assert sample_agent.sleep_max == 5


async def test_invalid_request(aiohttp_client, authorized_cookies, sample_agent):
    resp = await aiohttp_client.put('/api/rest', json=dict(index='agents', paw=sample_agent.paw,
                                                           sleep_min='notaninteger', sleep_max=5),
                                    cookies=authorized_cookies)
    assert resp.status == HTTPStatus.BAD_REQUEST
    messages = await resp.json()
    assert messages == dict(sleep_min=['Not a valid integer.'])


async def test_command_overwrite_failure(aiohttp_client, authorized_cookies):
    resp = await aiohttp_client.post('/api/rest',
                                     cookies=authorized_cookies,
                                     json=dict(index='configuration',
                                               prop='requirements',
                                               value=dict(go=dict(command='this should not get written',
                                                                  type='installed program',
                                                                  version='1.11',),
                                                          python=dict(attr='version',
                                                                      module='sys',
                                                                      type='python_module',
                                                                      version='3.6.1'))))

    assert resp.status == HTTPStatus.OK
    config_dict = await resp.json()
    assert config_dict.get('requirements', dict()).get('go', dict()).get('command') == 'go version'
