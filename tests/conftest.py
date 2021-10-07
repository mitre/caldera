import asyncio
import os.path
import pytest
import random
import string
import uuid
import yaml
import aiohttp_apispec

from unittest import mock
from aiohttp_apispec import validation_middleware
from aiohttp import web
from pathlib import Path

from app.api.v2.handlers.agent_api import AgentApi
from app.api.v2.handlers.ability_api import AbilityApi
from app.api.v2.handlers.objective_api import ObjectiveApi
from app.api.v2.handlers.adversary_api import AdversaryApi
from app.api.v2.handlers.operation_api import OperationApi
from app.api.v2.handlers.contact_api import ContactApi
from app.api.v2.handlers.obfuscator_api import ObfuscatorApi
from app.api.v2.handlers.plugins_api import PluginApi
from app.api.v2.handlers.health_api import HealthApi
from app.objects.c_obfuscator import Obfuscator
from app.utility.base_world import BaseWorld
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
from app.objects.c_adversary import Adversary
from app.objects.c_ability import Ability
from app.objects.c_operation import Operation
from app.objects.c_plugin import Plugin
from app.objects.c_agent import Agent
from app.objects.secondclass.c_executor import Executor
from app.objects.secondclass.c_link import Link
from app.objects.secondclass.c_fact import Fact
from app.objects.secondclass.c_relationship import Relationship
from app.objects.secondclass.c_rule import Rule
from app.api.v2.responses import json_request_validation_middleware
from app.api.v2.security import authentication_required_middleware_factory
from app.api.v2.responses import apispec_request_validation_middleware
from app.api.rest_api import RestApi
from app import version

DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(DIR, '..', 'conf')


@pytest.fixture(scope='session')
def init_base_world():
    with open(os.path.join(CONFIG_DIR, 'default.yml')) as c:
        BaseWorld.apply_config('main', yaml.load(c, Loader=yaml.FullLoader))
    BaseWorld.apply_config('agents', BaseWorld.strip_yml(os.path.join(CONFIG_DIR, 'agents.yml'))[0])
    BaseWorld.apply_config('payloads', BaseWorld.strip_yml(os.path.join(CONFIG_DIR, 'payloads.yml'))[0])


@pytest.fixture(scope='class')
def app_svc():
    async def _init_app_svc():
        return AppService(None)

    def _app_svc(loop):
        return loop.run_until_complete(_init_app_svc())
    return _app_svc


@pytest.fixture(scope='class')
def data_svc():
    return DataService()


@pytest.fixture(scope='class')
def knowledge_svc():
    return KnowledgeService()


@pytest.fixture(scope='class')
def file_svc():
    return FileSvc()


@pytest.fixture(scope='class')
def contact_svc():
    return ContactService()


@pytest.fixture(scope='class')
def event_svc(contact_svc, init_base_world):
    return EventService()


@pytest.fixture(scope='class')
def rest_svc():
    """
    The REST service requires the test's loop in order to be initialized in the same Thread
    as the test. This mitigates the issue where the service's calls to `asyncio.get_event_loop`
    would result in a RuntimeError indicating that there is no currentevent loop in the main
    thread.
    """
    async def _init_rest_svc():
        return RestService()

    def _rest_svc(loop):
        return loop.run_until_complete(_init_rest_svc())
    return _rest_svc


@pytest.fixture(scope='class')
def planning_svc():
    return PlanningService()


@pytest.fixture(scope='class')
def learning_svc():
    return LearningService()


@pytest.fixture(scope='class')
def services(app_svc):
    return app_svc.get_services()


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
        return Ability(ability_id=ability_id, *args, **kwargs)

    return _generate_ability


@pytest.fixture
def operation():
    def _generate_operation(name, agents, adversary, *args, **kwargs):
        return Operation(name=name, agents=agents, adversary=adversary, *args, **kwargs)

    return _generate_operation


@pytest.fixture
def demo_operation(loop, data_svc, operation, adversary):
    tadversary = loop.run_until_complete(data_svc.store(adversary()))
    return operation(name='my first op', agents=[], adversary=tadversary)


@pytest.fixture
def obfuscator(loop, data_svc):
    loop.run_until_complete(data_svc.store(
        Obfuscator(name='plain-text',
                   description='Does no obfuscation to any command, instead running it in plain text',
                   module='plugins.stockpile.app.obfuscators.plain_text')
        )
    )


@pytest.fixture
def agent():
    def _generate_agent(sleep_min, sleep_max, watchdog, *args, **kwargs):
        return Agent(sleep_min=sleep_min, sleep_max=sleep_max, watchdog=watchdog, *args, **kwargs)

    return _generate_agent


@pytest.fixture
def link():
    def _generate_link(command, paw, ability, executor, *args, **kwargs):
        return Link.load(dict(ability=ability, executor=executor, command=command, paw=paw, *args, **kwargs))

    return _generate_link


@pytest.fixture
def fact():
    def _generate_fact(trait, *args, **kwargs):
        return Fact(trait=trait, *args, **kwargs)

    return _generate_fact


@pytest.fixture
def rule():
    def _generate_rule(action, trait, *args, **kwargs):
        return Rule(action=action, trait=trait, *args, **kwargs)

    return _generate_rule


@pytest.fixture
def relationship():
    def _generate_relationship(source, edge, target, *args, **kwargs):
        return Relationship(source=source, edge=edge, target=target, *args, **kwargs)

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
def api_v2_client(loop, aiohttp_client, contact_svc):
    def make_app(svcs):
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
        HealthApi(svcs).add_routes(app)
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
        _ = LearningService()
        auth_svc = AuthService()
        _ = FileSvc()
        _ = EventService()
        services = app_svc.get_services()
        os.chdir(str(Path(__file__).parents[1]))

        await app_svc.register_contacts()
        _ = await RestApi(services).enable()
        await auth_svc.apply(app_svc.application, auth_svc.get_config('users'))
        await auth_svc.set_login_handlers(services)

        app_svc.register_subapp('/api/v2', make_app(svcs=services))
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

        return app_svc.application

    app = loop.run_until_complete(initialize())
    return loop.run_until_complete(aiohttp_client(app))


@pytest.fixture
def api_cookies(loop, api_v2_client):
    async def get_cookie():
        r = await api_v2_client.post('/enter', allow_redirects=False, data=dict(username='admin', password='admin'))
        return r.cookies
    return loop.run_until_complete(get_cookie())


@pytest.fixture
def async_return():
    def _async_return(return_param):
        f = asyncio.Future()
        f.set_result(return_param)
        return f
    return _async_return
