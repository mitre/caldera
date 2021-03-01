import pytest
import random
import string
import uuid
import yaml
from unittest import mock

from app.objects.c_obfuscator import Obfuscator
from app.utility.base_world import BaseWorld
from app.service.app_svc import AppService
from app.service.data_svc import DataService
from app.service.contact_svc import ContactService
from app.service.file_svc import FileSvc
from app.service.learning_svc import LearningService
from app.service.planning_svc import PlanningService
from app.service.rest_svc import RestService
from app.objects.c_adversary import Adversary
from app.objects.c_ability import Ability
from app.objects.c_operation import Operation
from app.objects.c_plugin import Plugin
from app.objects.c_agent import Agent
from app.objects.secondclass.c_link import Link
from app.objects.secondclass.c_fact import Fact


@pytest.fixture(scope='session')
def init_base_world():
    with open('conf/default.yml') as c:
        BaseWorld.apply_config('main', yaml.load(c, Loader=yaml.FullLoader))
    BaseWorld.apply_config('agents', BaseWorld.strip_yml('conf/agents.yml')[0])
    BaseWorld.apply_config('payloads', BaseWorld.strip_yml('conf/payloads.yml')[0])


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
def file_svc():
    return FileSvc()


@pytest.fixture(scope='class')
def contact_svc():
    return ContactService()


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
def ability():
    def _generate_ability(ability_id=None, variations=None, *args, **kwargs):
        if not ability_id:
            ability_id = random.randint(0, 999999)
        if not variations:
            variations = []
        return Ability(ability_id=ability_id, variations=variations, *args, **kwargs)

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
    def _generate_link(command, paw, ability, *args, **kwargs):
        return Link.load(dict(ability=ability, command=command, paw=paw, *args, **kwargs))

    return _generate_link


@pytest.fixture
def fact():
    def _generate_fact(trait, *args, **kwargs):
        return Fact(trait=trait, *args, **kwargs)

    return _generate_fact


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
