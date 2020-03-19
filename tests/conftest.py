import random
import pytest

from app.service.app_svc import AppService
from app.service.data_svc import DataService
from app.service.learning_svc import LearningService
from app.service.planning_svc import PlanningService
from app.service.rest_svc import RestService
from app.objects.c_ability import Ability
from app.objects.c_operation import Operation
from app.objects.c_agent import Agent
from app.objects.secondclass.c_link import Link


@pytest.fixture(scope='class')
def app_svc():
    return AppService(None)


@pytest.fixture(scope='class')
def data_svc():
    return DataService()


@pytest.fixture(scope='class')
def rest_svc():
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
def services():
    return app_svc.get_services()


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
        return Operation(name=name, agents=agent, adversary=adversary, *args, **kwargs)

    return _generate_operation


@pytest.fixture
def agent():
    def _generate_agent(sleep_min, sleep_max, watchdog, *args, **kwargs):
        return Agent(sleep_min=sleep_min, sleep_max=sleep_max, watchdog=watchdog, *args, **kwargs)

    return _generate_agent


@pytest.fixture
def link():
    def _generate_link(operation, command, paw, ability, *args, **kwargs):
        return Link(operation=operation, ability=ability, command=command, paw=paw, *args, **kwargs)

    return _generate_link
