import pytest
import yaml
import os
import aiohttp_apispec
from aiohttp_apispec import validation_middleware

from aiohttp import web
from pathlib import Path
from http import HTTPStatus

from app import version
from app.objects.c_operation import Operation
from app.objects.c_adversary import Adversary
from app.objects.c_agent import Agent
from app.objects.c_source import Source
from app.utility.base_world import BaseWorld
from app.api.v2.responses import json_request_validation_middleware
from app.api.v2.security import authentication_required_middleware_factory
from app.api.v2.responses import apispec_request_validation_middleware
from app.service.app_svc import AppService
from app.service.auth_svc import AuthService
from app.service.contact_svc import ContactService
from app.service.file_svc import FileSvc
from app.service.learning_svc import LearningService
from app.service.planning_svc import PlanningService
from app.api.v2.handlers.operation_api import OperationApi
from app.api.rest_api import RestApi


@pytest.fixture
def aiohttp_client(loop, aiohttp_client, data_svc):
    async def initialize():
        with open(Path(__file__).parents[4] / 'conf' / 'default.yml', 'r') as fle:
            BaseWorld.apply_config('main', yaml.safe_load(fle))
        with open(Path(__file__).parents[4] / 'conf' / 'payloads.yml', 'r') as fle:
            BaseWorld.apply_config('payloads', yaml.safe_load(fle))

        _ = PlanningService()
        _ = LearningService()
        auth_svc = AuthService()
        _ = ContactService()
        _ = FileSvc()

        def make_app(svcs):
            app = web.Application(
                middlewares=[
                    authentication_required_middleware_factory(services['auth_svc']),
                    json_request_validation_middleware
                ]
            )
            OperationApi(svcs).add_routes(app)
            return app

        app_svc = AppService(web.Application())
        services = app_svc.get_services()
        os.chdir(str(Path(__file__).parents[4]))
        app_svc.register_subapp('/api/v2', make_app(services))
        aiohttp_apispec.setup_aiohttp_apispec(
            app=app_svc.application,
            title='CALDERA',
            version=version.get_version(),
            swagger_path='/api/docs',
            url='/api/docs/swagger.json',
            static_path='/static/swagger'
        )
        app_svc.application.middlewares.append(apispec_request_validation_middleware)
        app_svc.application.middlewares.append(validation_middleware)

        await app_svc.register_contacts()
        _ = await RestApi(services).enable()
        await auth_svc.apply(app_svc.application, auth_svc.get_config('users'))
        await auth_svc.set_login_handlers(services)
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
def setup_operations_api_test(loop, data_svc):
    expected_adversary = {'description': 'an empty adversary profile', 'name': 'ad-hoc',
                          'adversary_id': 'ad-hoc', 'atomic_ordering': [],
                          'objective': '495a9828-cab1-44dd-a0ca-66e58177d8cc',
                          'tags': [], 'has_repeatable_abilities': False}
    expected_operation = {'name': 'My Test Operation',
                          'adversary': expected_adversary,
                          'state': 'finished',
                          'planner': {'name': 'test', 'description': None, 'module': 'test',
                                      'stopping_conditions': [], 'params': {}, 'allow_repeatable_abilities': False,
                                      'ignore_enforcement_modules': [], 'id': '123'}, 'jitter': '2/8',
                          'host_group': [{'trusted': True, 'architecture': 'unknown', 'watchdog': 0,
                                          'contact': 'unknown', 'username': 'unknown', 'links': [], 'sleep_max': 8,
                                          'exe_name': 'unknown', 'executors': ['pwsh', 'psh'], 'ppid': 0,
                                          'sleep_min': 2, 'server': '://None:None', 'platform': 'windows',
                                          'host': 'unknown', 'paw': '123', 'pid': 0,
                                          'display_name': 'unknown$unknown', 'group': 'red', 'location': 'unknown',
                                          'privilege': 'User', 'proxy_receivers': {}, 'proxy_chain': [],
                                          'origin_link_id': 0, 'deadman_enabled': False,
                                          'available_contacts': ['unknown'], 'pending_contact': 'unknown',
                                          'host_ip_addrs': [], 'upstream_dest': '://None:None'}],
                          'visibility': 50, 'autonomous': 1, 'chain': [], 'auto_close': False,
                          'obfuscator': 'plain-text', 'use_learning_parsers': False,
                          'objective': {'goals': [{'value': 'complete',
                                                   'operator': '==',
                                                   'target': 'exhaustion',
                                                   'achieved': False,
                                                   'count': 1048576}],
                                        'percentage': 0.0, 'description': '',
                                        'id': '495a9828-cab1-44dd-a0ca-66e58177d8cc',
                                        'name': 'default'}}
    test_adversary = Adversary(name=expected_adversary['name'], adversary_id=expected_adversary['adversary_id'],
                               description=expected_adversary['description'], objective=expected_adversary['objective'],
                               tags=expected_adversary['tags'])
    loop.run_until_complete(data_svc.store(test_adversary))

    test_agent = Agent(paw='123', sleep_min=2, sleep_max=8, watchdog=0, executors=['pwsh', 'psh'], platform='windows')
    loop.run_until_complete(data_svc.store(test_agent))

    test_source = Source(id='123', name='test', facts=[], adjustments=[])
    loop.run_until_complete(data_svc.store(test_source))

    test_operation = Operation(name=expected_operation['name'], adversary=test_adversary, agents=[test_agent], id='123',
                               source=test_source, state=expected_operation['state'])
    loop.run_until_complete(data_svc.store(test_operation))


@pytest.mark.usefixtures(
    "setup_operations_api_test"
)
class TestOperationsApi:
    async def test_get_operations(self, aiohttp_client, authorized_cookies):
        resp = await aiohttp_client.get('/api/v2/operations', cookies=authorized_cookies)
        operations_list = await resp.json()
        assert len(operations_list) == 1
        operation_dict = operations_list[0]
        assert operation_dict['name'] == 'My Test Operation'
        assert operation_dict['id'] == '123'

    async def test_get_operation_by_id(self, aiohttp_client, authorized_cookies):
        resp = await aiohttp_client.get('/api/v2/operations/123', cookies=authorized_cookies)
        operation_dict = await resp.json()
        assert operation_dict['name'] == 'My Test Operation'
        assert operation_dict['id'] == '123'

    async def test_unauthorized_get_operation_by_id(self, aiohttp_client):
        resp = await aiohttp_client.get('/api/v2/operations')
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_delete_operation_by_id(self, data_svc, aiohttp_client, authorized_cookies):
        op_exists = await data_svc.locate('operations', {'id': '123'})
        assert op_exists
        resp = await aiohttp_client.delete('/api/v2/operations/123', cookies=authorized_cookies)
        assert resp.status == HTTPStatus.NO_CONTENT
        op_exists = await data_svc.locate('operations', {'id': '123'})
        assert not op_exists

    async def test_get_operation_report(self, data_svc, aiohttp_client, authorized_cookies):
        resp = await aiohttp_client.get('/api/v2/operations/123', cookies=authorized_cookies)
        report = await resp.json()
        assert report['name'] == 'My Test Operation'
        assert report['state'] == 'finished'
