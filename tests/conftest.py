import asyncio
import os.path
import copy
import jinja2
import pytest
import random
import string
import uuid
import yaml
import aiohttp_apispec
import warnings

from datetime import datetime, timezone
from base64 import b64encode
from unittest import mock
from aiohttp_apispec import validation_middleware
from aiohttp import web
import aiohttp_jinja2
from pathlib import Path
from app.api.v2.handlers.agent_api import AgentApi
from app.api.v2.handlers.ability_api import AbilityApi
from app.api.v2.handlers.objective_api import ObjectiveApi
from app.api.v2.handlers.adversary_api import AdversaryApi
from app.api.v2.handlers.operation_api import OperationApi
from app.api.v2.handlers.contact_api import ContactApi
from app.api.v2.handlers.obfuscator_api import ObfuscatorApi
from app.api.v2.handlers.plugins_api import PluginApi
from app.api.v2.handlers.fact_source_api import FactSourceApi
from app.api.v2.handlers.fact_api import FactApi
from app.api.v2.handlers.planner_api import PlannerApi
from app.api.v2.handlers.health_api import HealthApi
from app.api.v2.handlers.schedule_api import ScheduleApi
from app.api.v2.handlers.payload_api import PayloadApi
from app.objects.c_obfuscator import Obfuscator
from app.objects.c_objective import Objective
from app.objects.c_planner import PlannerSchema
from app.objects.c_source import SourceSchema, Source
from app.service.app_svc import AppService
from app.service.auth_svc import AuthService
from app.service.data_svc import DataService
from app.service.contact_svc import ContactService
from app.service.event_svc import EventService
from app.service.file_svc import FileSvc
from app.service.learning_svc import LearningService
from app.service.planning_svc import PlanningService
from app.service.rest_svc import RestService
from app.service.knowledge_svc import KnowledgeService
from app.objects.c_adversary import Adversary, AdversarySchema
from app.objects.c_ability import Ability, AbilitySchema
from app.objects.c_operation import Operation, OperationSchema
from app.objects.c_plugin import Plugin
from app.objects.c_agent import Agent
from app.objects.secondclass.c_link import Link
from app.objects.secondclass.c_executor import Executor, ExecutorSchema
from app.objects.secondclass.c_link import Link
from app.objects.secondclass.c_fact import Fact
from app.objects.secondclass.c_relationship import Relationship
from app.objects.secondclass.c_rule import Rule
from app.utility.base_object import BaseObject
from app.utility.base_service import BaseService
from app.utility.base_world import BaseWorld
from app.api.v2.responses import json_request_validation_middleware
from app.api.v2.security import authentication_required_middleware_factory
from app.api.v2.responses import apispec_request_validation_middleware
from app.api.rest_api import RestApi

from app import version
from tests import AsyncMock

DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(DIR, '..', 'conf')

@pytest.fixture
def event_svc():
    return BaseService.get_service('event_svc')

@pytest.fixture
def data_svc():
    svc = BaseService.get_service('data_svc')
    assert svc is not None, "data_svc has not been initialized. Did you forget `DataService()`?"
    return svc
    return KnowledgeService()

@pytest.fixture
def knowledge_svc(api_v2_client):
    return BaseService.get_service('knowledge_svc')

@pytest.fixture(scope='class')
def file_svc(api_v2_client):
    return BaseService.get_service('file_svc')

@pytest.fixture
async def contact_svc():
    contact_svc = ContactService()
    yield contact_svc
    await contact_svc.deregister_contacts()

@pytest.fixture
def rest_svc():
    return BaseService.get_service('rest_svc')


@pytest.fixture(scope='class')
def planning_svc(api_v2_client):
    return PlanningService()

@pytest.fixture(scope='class')
def learning_svc():
    return LearningService()

@pytest.fixture(scope='class')
def mocker():
    return mock

@pytest.fixture
def adversary():
    def _generate_adversary(adversary_id=None, name=None, description=None, phases=None):
        if not adversary_id:
            adversary_id = uuid.uuid4()
        if not name:
            name = ''.join(random.choice(string.ascii_uppercase) for _ in range(10))
        if not description:
            description = "description"
        if not phases:
            phases = dict()
        return Adversary(adversary_id=adversary_id, name=name, description=description, atomic_ordering=phases)

    return _generate_adversary

@pytest.fixture
def executor():
    def _generate_executor(name='psh', platform='windows', *args, **kwargs):
        return Executor(name, platform, *args, **kwargs)

    return _generate_executor

@pytest.fixture
def ability():
    def _generate_ability(ability_id=None, *args, **kwargs):
        if not ability_id:
            ability_id = random.randint(0, 999999)
        return Ability(*args, ability_id=ability_id, **kwargs)

    return _generate_ability

@pytest.fixture
def operation():
    def _generate_operation(name, agents, adversary, *args, **kwargs):
        return Operation(*args, name=name, agents=agents, adversary=adversary, **kwargs)

    return _generate_operation

@pytest.fixture
async def demo_operation(data_svc, operation, adversary):
    tadversary = await data_svc.store(adversary())
    return operation(name='my first op', agents=[], adversary=tadversary)

@pytest.fixture
async def obfuscator(data_svc):
    await data_svc.store(
        Obfuscator(name='plain-text',
                   description='Does no obfuscation to any command, instead running it in plain text',
                   module='plugins.stockpile.app.obfuscators.plain_text')
        )

@pytest.fixture
def agent():
    def _generate_agent(sleep_min, sleep_max, watchdog, *args, **kwargs):
        return Agent(*args, sleep_min=sleep_min, sleep_max=sleep_max, watchdog=watchdog, **kwargs)

    return _generate_agent

@pytest.fixture
def link():
    def _generate_link(command, paw, ability, executor, *args, **kwargs):
        return Link.load(dict(*args, ability=ability, executor=executor, command=command, paw=paw, **kwargs))

    return _generate_link

@pytest.fixture
async def fact():
    async def _generate_fact(trait, *args, **kwargs):
        return Fact(*args, trait=trait, **kwargs)
    return _generate_fact

@pytest.fixture
def rule():
    def _generate_rule(action, trait, *args, **kwargs):
        return Rule(*args, action=action, trait=trait, **kwargs)

    return _generate_rule

@pytest.fixture
def relationship():
    def _generate_relationship(source, edge, target, *args, **kwargs):
        return Relationship(*args, source=source, edge=edge, target=target, **kwargs)

    return _generate_relationship

@pytest.fixture
def demo_plugin():
    def _generate_plugin(enabled=False, gui=False, data_dir=None, access=None):
        name = ''.join(random.choice(string.ascii_lowercase) for _ in range(10))
        desc = 'this is a good description'
        address = '/plugin/%s/gui' % name if gui else None
        return Plugin(name=name, description=desc, address=address, enabled=enabled, data_dir=data_dir, access=access)

    return _generate_plugin

@pytest.fixture
def agent_profile():
    def _agent_profile(paw=None, group='red', platform='linux', executors=None, privilege='Elevated'):
        if not executors:
            executors = ['sh']
        return dict(
            server='http://127.0.0.1:8888',
            username='username',
            group=group,
            host='hostname',
            platform=platform,
            architecture='x86_64',
            location='/path/to/agent',
            pid=random.randint(2, 32768),
            ppid=random.randint(2, 32768),
            executors=executors,
            privilege=privilege,
            exe_name='agent-exe-name',
            paw=paw
        )

    return _agent_profile

@pytest.fixture
def app_config():
    return {
        'app.contact.dns.domain': 'mycaldera.caldera',
        'app.contact.dns.socket': '0.0.0.0:8853',
        'app.contact.html': '/weather',
        'app.contact.http': '0.0.0.0:8888',
        'app.contact.tcp': '0.0.0.0:7010',
        'app.contact.tunnel.ssh.socket': '0.0.0.0:8022',
        'app.contact.udp': '0.0.0.0:7013',
        'app.contact.websocket': '0.0.0.0:7012',
        'plugins': [
            'stockpile',
            'atomic'
        ],
        'host': '0.0.0.0',
        'auth.login.handler.module': 'default',
        'users': {
            'red': {
                'red': 'password-foo'
            },
            'blue': {
                'blue': 'password-bar'
            }
        }
    }

@pytest.fixture
def agent_config():
    return {
        'sleep_min': '30',
        'sleep_max': '60',
        'untrusted_timer': '90',
        'watchdog': '0',
        'implant_name': 'splunkd',
        'deadman_abilities': [
            'this-is-a-fake-ability'
        ],
        'bootstrap_abilities': [
            'this-is-another-fake-ability'
        ]
    }

@pytest.fixture
async def api_v2_client(aiohttp_client, contact_svc):
    def make_app(svcs):
        warnings.filterwarnings(
            "ignore",
            message="Multiple schemas resolved to the name"
        )

        app = web.Application(
            middlewares=[
                authentication_required_middleware_factory(svcs['auth_svc']),
                json_request_validation_middleware
            ]
        )
        AgentApi(svcs).add_routes(app)
        AbilityApi(svcs).add_routes(app)
        OperationApi(svcs).add_routes(app)
        AdversaryApi(svcs).add_routes(app)
        ContactApi(svcs).add_routes(app)
        ObjectiveApi(svcs).add_routes(app)
        ObfuscatorApi(svcs).add_routes(app)
        PluginApi(svcs).add_routes(app)
        FactApi(svcs).add_routes(app)
        FactSourceApi(svcs).add_routes(app)
        PlannerApi(svcs).add_routes(app)
        HealthApi(svcs).add_routes(app)
        ScheduleApi(svcs).add_routes(app)
        PayloadApi(svcs).add_routes(app)
        return app

    async def initialize():
        with open(Path(__file__).parents[1] / 'conf' / 'default.yml', 'r') as fle:
            BaseWorld.apply_config('main', yaml.safe_load(fle))
        with open(Path(__file__).parents[1] / 'conf' / 'payloads.yml', 'r') as fle:
            BaseWorld.apply_config('payloads', yaml.safe_load(fle))

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
        os.chdir(str(Path(__file__).parents[1]))

        _ = await RestApi(services).enable()
        await app_svc.register_contacts()
        await auth_svc.apply(app_svc.application, auth_svc.get_config('users'))
        await auth_svc.set_login_handlers(services)

        app_svc.register_subapp('/api/v2', make_app(svcs=services))
        aiohttp_apispec.setup_aiohttp_apispec(
            app=app_svc.application,
            title='Caldera',
            version=version.get_version(),
            swagger_path='/api/docs',
            url='/api/docs/swagger.json',
            static_path='/static/swagger'
        )
        app_svc.application.middlewares.append(apispec_request_validation_middleware)
        app_svc.application.middlewares.append(validation_middleware)
        templates = ['plugins/%s/templates' % p.lower() for p in app_svc.get_config('plugins')]
        templates.append('plugins/magma/dist')
        templates.append("templates")
        aiohttp_jinja2.setup(app_svc.application, loader=jinja2.FileSystemLoader(templates))
        return app_svc

    app_svc = await initialize()
    app = app_svc.application
    yield await aiohttp_client(app)
    await app_svc._destroy_plugins()

@pytest.fixture
async def api_cookies(api_v2_client):
    r = await api_v2_client.post('/enter', allow_redirects=False, data=dict(username='admin', password='admin'))
    return r.cookies

@pytest.fixture
def async_return():
    def _async_return(return_param):
        f = asyncio.Future()
        f.set_result(return_param)
        return f
    return _async_return

@pytest.fixture
def mock_time():
    return datetime(2021, 1, 1, tzinfo=timezone.utc)

@pytest.fixture
def parse_datestring():
    def _parse_datestring(datestring):
        return datetime.strptime(datestring, BaseObject.TIME_FORMAT)
    return _parse_datestring

@pytest.fixture
async def test_adversary(api_v2_client):
    expected_adversary = {
        'name': 'ad-hoc',
        'description': 'an empty adversary profile',
        'adversary_id': 'ad-hoc',
        'objective': '495a9828-cab1-44dd-a0ca-66e58177d8cc',
        'tags': [],
        'has_repeatable_abilities': False
    }
    test_adversary = AdversarySchema().load(expected_adversary)
    assert test_adversary is not None, "AdversarySchema().load() returned None"
    data_svc = BaseService.get_service('data_svc')
    assert data_svc is not None, "data_svc must be initialized"
    await data_svc.store(test_adversary)
    return test_adversary

@pytest.fixture
async def test_planner(api_v2_client):
    expected_planner = {
        'name': 'test planner',
        'description': 'test planner',
        'module': 'test',
        'stopping_conditions': [],
        'params': {},
        'allow_repeatable_abilities': False,
        'ignore_enforcement_modules': [],
        'id': '123'
    }
    test_planner = PlannerSchema().load(expected_planner)
    data_svc = BaseService.get_service('data_svc')
    assert data_svc is not None
    await data_svc.store(test_planner)
    return test_planner

@pytest.fixture
async def test_source(api_v2_client):
    test_fact = Fact(trait='remote.host.fqdn', value='dc')
    test_source = Source(id='123', name='test', facts=[test_fact], adjustments=[])
    data_svc = BaseService.get_service('data_svc')
    assert data_svc is not None
    await data_svc.store(test_source)
    return test_source

@pytest.fixture
async def test_source_existing_relationships(api_v2_client):
    test_fact_1 = Fact(trait='test_1', value='1')
    test_fact_2 = Fact(trait='test_2', value='2')
    test_relationship = Relationship(source=test_fact_1, edge='test_edge', target=test_fact_2)
    test_source = Source(id='123', name='test', facts=[test_fact_1, test_fact_2], adjustments=[],
                         relationships=[test_relationship])
    data_svc = BaseService.get_service('data_svc')
    assert data_svc is not None
    await data_svc.store(test_source)
    return test_source

@pytest.fixture
def test_operation(test_adversary, test_planner, test_source):
    expected_operation = {'name': '123',
                          'adversary': AdversarySchema().dump(test_adversary),
                          'state': 'paused',
                          'id': '123',
                          'group': 'red',
                          'autonomous': 0,
                          'planner': PlannerSchema().dump(test_planner),
                          'source': SourceSchema().dump(test_source),
                          'jitter': '2/8',
                          'visibility': 50,
                          'auto_close': False,
                          'obfuscator': 'plain-text',
                          'use_learning_parsers': False}
    def _copy():
        return copy.deepcopy(expected_operation)
    return _copy

@pytest.fixture
async def test_agent(api_v2_client):
    agent = Agent(paw='123', sleep_min=2, sleep_max=8, watchdog=0, executors=['sh'], platform='linux', host='test-host')
    data_svc = BaseService.get_service('data_svc')
    assert data_svc is not None
    await data_svc.store(agent)
    return agent

@pytest.fixture
async def test_executor(test_agent):
    return Executor(**dict(timeout=60, platform=test_agent.platform, name='sh', command='ls'))

@pytest.fixture
async def test_ability(test_executor, api_v2_client):
    ability_dict = {
        'ability_id': '123',
        'tactic': 'discovery',
        'technique_id': 'auto-generated',
        'technique_name': 'auto-generated',
        'name': 'Manual Command',
        'description': 'test ability',
        'executors': [ExecutorSchema().dump(test_executor)]
    }
    ability = AbilitySchema().load(ability_dict)
    data_svc = BaseService.get_service('data_svc')
    assert data_svc is not None
    await data_svc.store(ability)
    return ability

@pytest.fixture
def expected_link_output():
    return 'test_dir'

@pytest.fixture
def active_link(test_executor, test_agent, test_ability):
    return Link(
        command=str(b64encode(test_executor.command.encode()), 'utf-8'),
        paw=test_agent.paw,
        ability=test_ability,
        executor=test_executor,
        score=0,
        jitter=0,
        cleanup=0,
        pin=0,
        host=test_agent.host,
        deadman=False,
        used=[],
        id='456',
        relationships=[]
    )

@pytest.fixture
def finished_link(test_executor, test_agent, test_ability):
    link = Link(
        command=str(b64encode(test_executor.command.encode()), 'utf-8'),
        paw=test_agent.paw,
        ability=test_ability,
        executor=test_executor,
        host=test_agent.host,
        deadman=False,
        used=[],
        id='789',
        relationships=[],
        status=0,
    )
    link.output = 'test_dir'
    return link

@pytest.fixture
async def finished_operation_payload(test_operation):
    op_id = "00000000-0000-0000-0000-000000000000"
    op_data = test_operation()
    op_data['id'] = op_id
    op_data['name'] = op_id
    op_data['state'] = 'finished'
    return op_data

@pytest.fixture
async def setup_finished_operation(finished_operation_payload):
    op_data = finished_operation_payload
    op = OperationSchema().load(op_data)
    data_svc = BaseService.get_service('data_svc')
    assert data_svc is not None
    await data_svc.store(op)
    return op

@pytest.fixture
async def setup_operations_api_test(api_v2_client, test_operation, test_agent, test_ability,
                                    active_link, finished_link, expected_link_output):
    op_data = test_operation()
    op = OperationSchema().load(op_data)
    op.agents.append(test_agent)
    op.set_start_details()
    test_link = active_link
    test_link.host = test_agent.host
    fin_link = finished_link
    fin_link.output = expected_link_output
    fin_link.host = test_agent.host
    op.chain.append(test_link)
    op.chain.append(fin_link)
    op.objective = Objective(id='123', name='test objective', description='test', goals=[])
    data_svc = BaseService.get_service('data_svc')
    assert data_svc is not None
    await data_svc.store(op)

@pytest.fixture
async def setup_empty_operation(test_operation):
    op_data = test_operation()
    op = OperationSchema().load(op_data)
    op.set_start_details()
    op.objective = Objective(id='123', name='test objective', description='test', goals=[])
    data_svc = BaseService.get_service('data_svc')
    assert data_svc is not None
    await data_svc.store(op)

@pytest.fixture()
def fire_event_mock(event_svc):
    """A mock for event_svc.fire_event()

    fire_event()  wont work in tests as underlying Application
    is a stub so mock call here
    """
    event_svc.fire_event = AsyncMock(return_value=None)
