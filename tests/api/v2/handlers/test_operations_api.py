import pytest

from http import HTTPStatus
from base64 import b64encode

from app.objects.c_ability import AbilitySchema
from app.objects.c_operation import OperationSchema
from app.objects.c_adversary import AdversarySchema
from app.objects.c_agent import Agent
from app.objects.c_objective import Objective
from app.objects.c_planner import PlannerSchema
from app.objects.c_source import Source, SourceSchema
from app.objects.secondclass.c_executor import ExecutorSchema
from app.objects.secondclass.c_fact import Fact
from app.objects.secondclass.c_link import Link
from app.utility.base_service import BaseService


@pytest.fixture
def test_adversary(loop):
    expected_adversary = {'name': 'ad-hoc',
                          'description': 'an empty adversary profile',
                          'adversary_id': 'ad-hoc',
                          'objective': '495a9828-cab1-44dd-a0ca-66e58177d8cc',
                          'tags': [],
                          'has_repeatable_abilities': False}
    test_adversary = AdversarySchema().load(expected_adversary)
    loop.run_until_complete(BaseService.get_service('data_svc').store(test_adversary))
    return test_adversary


@pytest.fixture
def test_planner(loop):
    expected_planner = {'name': 'test planner',
                        'description': 'test planner',
                        'module': 'test',
                        'stopping_conditions': [],
                        'params': {},
                        'allow_repeatable_abilities': False,
                        'ignore_enforcement_modules': [],
                        'id': '123'}
    test_planner = PlannerSchema().load(expected_planner)
    loop.run_until_complete(BaseService.get_service('data_svc').store(test_planner))
    return test_planner


@pytest.fixture
def test_source(loop):
    test_fact = Fact(trait='remote.host.fqdn', value='dc')
    test_source = Source(id='123', name='test', facts=[test_fact], adjustments=[])
    loop.run_until_complete(BaseService.get_service('data_svc').store(test_source))
    return test_source


@pytest.fixture
def test_operation(test_adversary, test_planner, test_source):
    expected_operation = {'name': 'My Test Operation',
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

    return expected_operation


@pytest.fixture
def test_agent(loop):
    agent = Agent(paw='123', sleep_min=2, sleep_max=8, watchdog=0, executors=['sh'], platform='linux')
    loop.run_until_complete(BaseService.get_service('data_svc').store(agent))
    return agent


@pytest.fixture
def test_executor(test_agent):
    return ExecutorSchema().load(dict(timeout=60, platform=test_agent.platform, name='linux',
                                      command='ls'))


@pytest.fixture
def test_ability(test_executor, loop):
    ability = AbilitySchema().load(dict(ability_id='123',
                                        tactic='discovery',
                                        technique_id='auto-generated',
                                        technique_name='auto-generated',
                                        name='Manual Command',
                                        description='test ability',
                                        executors=[ExecutorSchema().dump(test_executor)]))
    loop.run_until_complete(BaseService.get_service('data_svc').store(ability))
    return ability


@pytest.fixture
def active_link(test_executor, test_agent, test_ability):
    return {
        'command': str(b64encode(test_executor.command.encode()), 'utf-8'),
        'paw': test_agent.paw,
        'ability': test_ability,
        'executor': test_executor,
        'score': 0,
        'jitter': 0,
        'cleanup': 0,
        'pin': 0,
        'host': test_agent.host,
        'deadman': False,
        'used': [],
        'id': '456',
        'relationships': []
    }


@pytest.fixture
def finished_link(test_executor, test_agent, test_ability):
    return {
        'command': test_executor.command,
        'paw': test_agent.paw,
        'ability': test_ability,
        'executor': test_executor,
        'host': test_agent.host,
        'deadman': False,
        'used': [],
        'id': '789',
        'relationships': [],
        'status': 0
    }


@pytest.fixture
def setup_operations_api_test(loop, api_v2_client, test_operation, test_agent, test_ability,
                              active_link, finished_link):
    test_operation = OperationSchema().load(test_operation)
    test_operation.agents.append(test_agent)
    test_operation.set_start_details()
    test_link = Link.load(active_link)
    test_link.host = test_agent.host
    finished_link = Link.load(finished_link)
    finished_link.host = test_agent.host
    test_operation.chain.append(test_link)
    test_operation.chain.append(finished_link)
    test_objective = Objective(id='123', name='test objective', description='test', goals=[])
    test_operation.objective = test_objective
    loop.run_until_complete(BaseService.get_service('data_svc').store(test_operation))


@pytest.mark.usefixtures(
    "setup_operations_api_test"
)
class TestOperationsApi:
    async def test_get_operation_link_result(self, api_v2_client, api_cookies, finished_link, mocker):
        with mocker.patch('app.service.file_svc.FileSvc.read_result_file') as mock_read_result:
            encoded_result = str(b64encode('user'.encode()), 'utf-8')
            mock_read_result.return_value = encoded_result
            resp = await api_v2_client.get('/api/v2/operations/123/links/789/result', cookies=api_cookies)
            assert resp.status == HTTPStatus.OK
            output = await resp.json()
            assert output['link']['id'] == finished_link['id']
            assert output['link']['paw'] == finished_link['paw']
            assert output['link']['command'] == finished_link['command']
            assert output['result'] == encoded_result

    async def test_unauthorized_get_operation_link_result(self, api_v2_client, finished_link):
        resp = await api_v2_client.get('/api/v2/operations/123/links/789/result')
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_get_operation_link_no_result(self, api_v2_client, api_cookies, active_link):
        resp = await api_v2_client.get('/api/v2/operations/123/links/456/result', cookies=api_cookies)
        assert resp.status == HTTPStatus.OK
        output = await resp.json()
        assert output['result'] == ""
        assert output['link']['paw'] == active_link['paw']
        assert output['link']['id'] == active_link['id']
        assert output['link']['command'] == active_link['command']

    async def test_nonexistent_get_operation_link_result(self, api_v2_client, api_cookies):
        resp = await api_v2_client.get('/api/v2/operations/123/links/999/result', cookies=api_cookies)
        assert resp.status == HTTPStatus.NOT_FOUND
