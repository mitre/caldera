import asyncio
import pytest

from app.service.app_svc import AppService
from app.service.data_svc import DataService
from app.service.learning_svc import LearningService
from app.service.planning_svc import PlanningService
from app.service.rest_svc import RestService


@pytest.fixture(scope='class')
def app_svc():
    return AppService(None)


@pytest.fixture(scope='class')
def data_svc():
    return DataService()


@pytest.fixture(scope='class')
def rest_svc():
    return RestService()


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
def run_async():
    def _run_async(c):
        return asyncio.get_event_loop().run_until_complete(c)
    return _run_async
