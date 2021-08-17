import pytest

from http import HTTPStatus

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
def expected_operation(test_adversary, test_planner, test_source):
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
                                      command='d2hvYW1p'))


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
        'command': test_executor.command,
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
def setup_finished_operation(loop, expected_operation):
    finished_operation = OperationSchema().load(expected_operation)
    finished_operation.id = '000'
    finished_operation.state = 'finished'
    loop.run_until_complete(BaseService.get_service('data_svc').store(finished_operation))


@pytest.fixture
def setup_operations_api_test(loop, api_client, expected_operation, test_agent, test_ability,
                              active_link, finished_link):
    test_operation = OperationSchema().load(expected_operation)
    test_operation.agents.append(test_agent)
    test_operation.set_start_details()
    test_operation.adversary.atomic_ordering.append(test_ability)
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
    async def test_get_operations(self, api_client, api_cookies, expected_operation):
        resp = await api_client.get('/api/v2/operations', cookies=api_cookies)
        operations_list = await resp.json()
        assert len(operations_list) == 1
        operation_dict = operations_list[0]
        assert operation_dict['name'] == expected_operation['name']
        assert operation_dict['id'] == expected_operation['id']
        assert operation_dict['group'] == expected_operation['group']
        assert operation_dict['state'] == expected_operation['state']

    async def test_unauthorized_get_operations(self, api_client):
        resp = await api_client.get('/api/v2/operations')
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_get_operation_by_id(self, api_client, api_cookies, expected_operation):
        resp = await api_client.get('/api/v2/operations/123', cookies=api_cookies)
        operation_dict = await resp.json()
        assert operation_dict['name'] == expected_operation['name']
        assert operation_dict['id'] == expected_operation['id']

    async def test_unauthorized_get_operation_by_id(self, api_client):
        resp = await api_client.get('/api/v2/operations/123')
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_nonexistent_operation_get_operation_by_id(self, api_client, api_cookies):
        resp = await api_client.get('/api/v2/operations/999', cookies=api_cookies)
        assert resp.status == HTTPStatus.NOT_FOUND

    async def test_get_operation_report(self, api_client, api_cookies, mocker, async_return, expected_operation):
        with mocker.patch('app.objects.c_operation.Operation.all_facts') as mock_all_facts:
            mock_all_facts.return_value = async_return([])
            resp = await api_client.get('/api/v2/operations/123/report', cookies=api_cookies)
            report = await resp.json()
            assert report['name'] == expected_operation['name']
            assert report['jitter'] == expected_operation['jitter']
            assert report['planner'] == expected_operation['planner']['name']
            assert report['adversary']['name'] == expected_operation['adversary']['name']
            assert report['start']

    async def test_unauthorized_get_operation_report(self, api_client):
        resp = await api_client.get('/api/v2/operations/123/report')
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_nonexistent_operation_get_operation_report(self, api_client, api_cookies):
        resp = await api_client.get('/api/v2/operations/999/report', cookies=api_cookies)
        assert resp.status == HTTPStatus.NOT_FOUND

    async def test_create_operation(self, api_client, api_cookies):
        payload = dict(name='post_test', planner={'id': '123'},
                       adversary={'adversary_id': '123', 'name': 'ad-hoc'}, source={'id': '123'})
        resp = await api_client.post('/api/v2/operations', cookies=api_cookies, json=payload)
        assert resp.status == HTTPStatus.OK
        op_exists = await BaseService.get_service('data_svc').locate('operations', {'name': 'post_test'})
        assert op_exists
        op_data = await resp.json()
        assert op_data['name'] == payload['name']
        assert op_data['start']
        assert op_data['planner']['id'] == payload['planner']['id']
        assert op_data['adversary']['name'] == payload['adversary']['name']
        assert op_data['source']['id'] == payload['source']['id']

    async def test_duplicate_create_operation(self, api_client, api_cookies, expected_operation):
        payload = dict(name='post_test', id=expected_operation['id'], planner={'id': '123'},
                       adversary={'adversary_id': '123'}, source={'id': '123'})
        resp = await api_client.post('/api/v2/operations', cookies=api_cookies, json=payload)
        assert resp.status == HTTPStatus.BAD_REQUEST

    async def test_create_finished_operation(self, api_client, api_cookies, expected_operation):
        payload = dict(name='post_test', id='111', planner={'id': '123'},
                       adversary={'adversary_id': '123'}, source={'id': '123'}, state='finished')
        resp = await api_client.post('/api/v2/operations', cookies=api_cookies, json=payload)
        assert resp.status == HTTPStatus.BAD_REQUEST

    async def test_unauthorized_create_operation(self, api_client):
        payload = dict(name='post_test', planner={'id': '123'},
                       adversary={'adversary_id': '123'}, source={'id': '123'})
        resp = await api_client.post('/api/v2/operations', json=payload)
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_update_operation(self, api_client, api_cookies, mocker, async_return, expected_operation):
        op_manager_path = 'app.api.v2.managers.operation_api_manager.OperationApiManager.validate_operation_state'
        with mocker.patch(op_manager_path) as mock_validate:
            mock_validate.return_value = async_return(True)
            payload = dict(state='running', obfuscator='base64')
            resp = await api_client.patch('/api/v2/operations/123', cookies=api_cookies, json=payload)
            assert resp.status == HTTPStatus.OK
            op = (await BaseService.get_service('data_svc').locate('operations', {'id': '123'}))[0]
            assert op.state == payload['state']
            assert op.obfuscator == payload['obfuscator']
            assert op.id == expected_operation['id']
            assert op.name == expected_operation['name']
            assert op.planner.planner_id == expected_operation['planner']['id']

    async def test_unauthorized_update_operation(self, api_client):
        payload = dict(state='running', obfuscator='base64')
        resp = await api_client.patch('/api/v2/operations/123', json=payload)
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_nonexistent_operation_update(self, api_client, api_cookies):
        payload = dict(state='running', obfuscator='base64')
        resp = await api_client.patch('/api/v2/operations/999', json=payload, cookies=api_cookies)
        assert resp.status == HTTPStatus.NOT_FOUND

    async def test_disallowed_fields_update_operation(self, api_client, api_cookies, mocker, async_return, expected_operation):
        op_manager_path = 'app.api.v2.managers.operation_api_manager.OperationApiManager.validate_operation_state'
        with mocker.patch(op_manager_path) as mock_validate:
            mock_validate.return_value = async_return(True)
            payload = dict(name='new operation', id='500')
            resp = await api_client.patch('/api/v2/operations/123', cookies=api_cookies, json=payload)
            assert resp.status == HTTPStatus.OK
            op = (await BaseService.get_service('data_svc').locate('operations', {'id': '123'}))[0]
            assert op.id == expected_operation['id']
            assert op.name == expected_operation['name']
            assert op.planner.name == expected_operation['planner']['name']

    async def test_update_finished_operation(self, api_client, api_cookies, setup_finished_operation):
        payload = dict(state='running', obfuscator='base64')
        resp = await api_client.patch('/api/v2/operations/000', cookies=api_cookies, json=payload)
        assert resp.status == HTTPStatus.BAD_REQUEST

    async def test_get_links(self, api_client, api_cookies, active_link):
        resp = await api_client.get('/api/v2/operations/123/links', cookies=api_cookies)
        assert resp.status == HTTPStatus.OK
        links = await resp.json()
        assert len(links) == 2
        assert links[0]['id'] == active_link['id']
        assert links[0]['paw'] == active_link['paw']
        assert links[0]['command'] == active_link['command']

    async def test_unauthorized_get_links(self, api_client):
        resp = await api_client.get('/api/v2/operations/123/links')
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_get_operation_link(self, api_client, api_cookies, active_link):
        resp = await api_client.get('/api/v2/operations/123/links/456', cookies=api_cookies)
        assert resp.status == HTTPStatus.OK
        link = await resp.json()
        assert link['id'] == active_link['id']
        assert link['paw'] == active_link['paw']
        assert link['command'] == active_link['command']

    async def test_unauthorized_get_operation_link(self, api_client):
        resp = await api_client.get('/api/v2/operations/123/links/456')
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_nonexistent_operation_get_operation_link(self, api_client, api_cookies):
        resp = await api_client.get('/api/v2/operations/999/links/123', cookies=api_cookies)
        assert resp.status == HTTPStatus.NOT_FOUND

    async def test_nonexistent_link_get_operation_link(self, api_client, api_cookies):
        resp = await api_client.get('/api/v2/operations/123/links/999', cookies=api_cookies)
        assert resp.status == HTTPStatus.NOT_FOUND

    async def test_update_operation_link(self, api_client, api_cookies, active_link):
        original_command = active_link['command']
        payload = dict(command='bHM=')
        resp = await api_client.patch('/api/v2/operations/123/links/456', cookies=api_cookies, json=payload)
        assert resp.status == HTTPStatus.OK
        op = (await BaseService.get_service('data_svc').locate('operations', {'id': '123'}))[0]
        assert op.chain[0].command != original_command
        assert op.chain[0].command == payload['command']
        assert op.chain[0].id == active_link['id']
        assert op.chain[0].paw == active_link['paw']

    async def test_unauthorized_update_operation_link(self, api_client):
        payload = dict(command='bHM=')
        resp = await api_client.patch('/api/v2/operations/123/links/456', json=payload)
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_nonexistent_operation_update_operation_link(self, api_client, api_cookies):
        payload = dict(command='bHM=')
        resp = await api_client.patch('/api/v2/operations/999/links/123', json=payload, cookies=api_cookies)
        assert resp.status == HTTPStatus.NOT_FOUND

    async def test_nonexistent_link_update_operation_link(self, api_client, api_cookies):
        payload = dict(command='bHM=')
        resp = await api_client.patch('/api/v2/operations/123/links/999', json=payload, cookies=api_cookies)
        assert resp.status == HTTPStatus.NOT_FOUND

    async def test_update_finished_operation_link(self, api_client, api_cookies):
        payload = dict(command='bHM=', status=-1)
        resp = await api_client.patch('/api/v2/operations/123/links/789', json=payload, cookies=api_cookies)
        assert resp.status == HTTPStatus.FORBIDDEN

    async def test_get_potential_links(self, api_client, api_cookies, mocker, async_return):
        BaseService.get_service('rest_svc').build_potential_abilities = mocker.Mock()
        BaseService.get_service('rest_svc').build_potential_abilities.return_value = async_return([])
        expected_link = Link(command='whoami', paw='123456', id='789')
        BaseService.get_service('rest_svc').build_potential_links = mocker.Mock()
        BaseService.get_service('rest_svc').build_potential_links.return_value = async_return([expected_link])
        resp = await api_client.get('/api/v2/operations/123/potential-links', cookies=api_cookies)
        result = await resp.json()
        assert len(result) == 1
        assert result[0]['id'] == expected_link.id
        assert result[0]['paw'] == expected_link.paw
        assert result[0]['command'] == expected_link.command

    async def test_unauthorized_get_potential_links(self, api_client):
        resp = await api_client.get('/api/v2/operations/123/potential-links')
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_nonexistent_operation_get_potential_links(self, api_client, api_cookies):
        resp = await api_client.get('/api/v2/operations/999/potential-links', cookies=api_cookies)
        assert resp.status == HTTPStatus.NOT_FOUND

    async def test_get_potential_links_by_paw(self, api_client, api_cookies, mocker, async_return, ability, executor):
        BaseService.get_service('rest_svc').build_potential_abilities = mocker.Mock()
        BaseService.get_service('rest_svc').build_potential_abilities.return_value = async_return([])
        expected_link = Link(command='whoami', paw='123456', id='789')
        BaseService.get_service('rest_svc').build_potential_links = mocker.Mock()
        BaseService.get_service('rest_svc').build_potential_links.return_value = async_return([expected_link])
        resp = await api_client.get('/api/v2/operations/123/potential-links/123', cookies=api_cookies)
        result = await resp.json()
        assert len(result) == 1
        assert result[0]['id'] == expected_link.id
        assert result[0]['paw'] == expected_link.paw
        assert result[0]['command'] == expected_link.command

    async def test_unauthorized_get_potential_links_by_paw(self, api_client):
        resp = await api_client.get('/api/v2/operations/123/potential-links/123')
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_nonexistent_operation_get_potential_links_by_paw(self, api_client, api_cookies):
        resp = await api_client.get('/api/v2/operations/999/potential-links/123', cookies=api_cookies)
        assert resp.status == HTTPStatus.NOT_FOUND

    async def test_nonexistent_agent_get_potential_links_by_paw(self, api_client, api_cookies):
        resp = await api_client.get('/api/v2/operations/123/potential-links/999', cookies=api_cookies)
        assert resp.status == HTTPStatus.NOT_FOUND

    async def test_create_potential_link(self, api_client, api_cookies, mocker, async_return):
        with mocker.patch('app.objects.c_operation.Operation.apply') as mock_apply:
            mock_apply.return_value = async_return(None)
            payload = {
                "paw": "123",
                "executor": {
                    "platform": "linux",
                    "name": "sh",
                    "command": "ls -a"
                },
                "status": -1
            }
            resp = await api_client.post('/api/v2/operations/123/potential-links', cookies=api_cookies, json=payload)
            result = await resp.json()
            assert result['paw'] == payload['paw']
            assert result['id']
            assert result['ability']['name'] == 'Manual Command'
            assert result['executor']['platform'] == payload['executor']['platform']

    async def test_unauthorized_create_potential_links(self, api_client):
        payload = {
            "paw": "123",
            "executor": {
                "platform": "linux",
                "name": "sh",
                "command": "ls -a"
            },
            "status": -1
        }
        resp = await api_client.post('/api/v2/operations/123/potential-links', json=payload)
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_nonexistent_operation_create_potential_links(self, api_client, api_cookies):
        payload = {
            "paw": "123",
            "executor": {
                "platform": "linux",
                "name": "sh",
                "command": "ls -a"
            },
            "status": -1
        }
        resp = await api_client.post('/api/v2/operations/999/potential-links', json=payload, cookies=api_cookies)
        assert resp.status == HTTPStatus.NOT_FOUND
