import os
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


@pytest.fixture
def sample_agent(loop, aiohttp_client):
    kwargs = {'architecture': 'amd64', 'exe_name': 'sandcat.go', 'executors': ['shellcode_amd64', 'sh'],
              'group': 'red', 'host': 'testsystem.localdomain', 'location': './sandcat.go', 'pid': 125266,
              'platform': 'linux', 'ppid': 124042, 'privilege': 'User', 'server': 'http://127.0.0.1:8888',
              'username': 'testuser', 'paw': None, 'contact': 'http'}

    agent = loop.run_until_complete(
        BaseService.get_service('data_svc').store(Agent(sleep_min=0, sleep_max=60, watchdog=0, **kwargs))
    )
    yield agent

    loop.run_until_complete(
        BaseService.get_service('data_svc').remove('agent', dict(paw=agent.paw))
    )
