import pytest

from http import HTTPStatus

from app.objects.c_ability import AbilitySchema
from app.objects.c_operation import OperationSchema
from app.objects.c_adversary import Adversary, AdversarySchema
from app.objects.c_agent import Agent
from app.objects.c_objective import Objective
from app.objects.c_planner import Planner, PlannerSchema
from app.objects.c_source import Source, SourceSchema
from app.objects.secondclass.c_executor import ExecutorSchema
from app.objects.secondclass.c_fact import Fact
from app.objects.secondclass.c_link import Link
from app.utility.base_service import BaseService


@pytest.fixture
def setup_operations_api_test(loop, api_client):
    expected_adversary = {'name': 'ad-hoc', 'description': 'an empty adversary profile',
                          'adversary_id': 'ad-hoc',
                          'objective': '495a9828-cab1-44dd-a0ca-66e58177d8cc',
                          'tags': [], 'has_repeatable_abilities': False}
    expected_planner = {'name': 'test', 'description': 'test planner', 'module': 'test',
                        'stopping_conditions': [], 'params': {}, 'allow_repeatable_abilities': False,
                        'ignore_enforcement_modules': [], 'id': '123'}
    test_adversary = Adversary(name=expected_adversary['name'], adversary_id=expected_adversary['adversary_id'],
                               description=expected_adversary['description'], objective=expected_adversary['objective'],
                               tags=expected_adversary['tags'])
    loop.run_until_complete(BaseService.get_service('data_svc').store(test_adversary))

    test_planner = Planner(name=expected_planner['name'], planner_id=expected_planner['id'],
                           description=expected_planner['description'], module=expected_planner['module'],
                           params=expected_planner['params'],
                           stopping_conditions=expected_planner['stopping_conditions'])
    loop.run_until_complete(BaseService.get_service('data_svc').store(test_planner))

    test_fact = Fact(trait='remote.host.fqdn', value='dc')
    test_source = Source(id='123', name='test', facts=[test_fact], adjustments=[])
    loop.run_until_complete(BaseService.get_service('data_svc').store(test_source))

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

    test_operation = OperationSchema().load(expected_operation)

    test_agent = Agent(paw='123', sleep_min=2, sleep_max=8, watchdog=0, executors=['sh'], platform='linux')
    test_operation.agents.append(test_agent)
    test_operation.set_start_details()
    loop.run_until_complete(BaseService.get_service('data_svc').store(test_agent))
    test_executor = ExecutorSchema().load(dict(timeout=60, platform=test_agent.platform, name='linux',
                                               command='d2hvYW1p'))
    test_ability = AbilitySchema().load(dict(ability_id='123', tactic='discovery', technique_id='auto-generated',
                                             technique_name='auto-generated', name='Manual Command',
                                             description='test ability',
                                             executors=[ExecutorSchema().dump(test_executor)]))
    test_operation.adversary.atomic_ordering.append(test_ability)
    loop.run_until_complete(BaseService.get_service('data_svc').store(test_ability))
    test_link = Link.load(dict(command=test_executor.command, paw=test_agent.paw, ability=test_ability,
                               executor=test_executor, status=test_operation.link_status(), score=0, jitter=0,
                               cleanup=0, pin=0, host=test_agent.host, deadman=False, used=[], id='456',
                               relationships=[]))
    test_link.host = test_agent.host
    test_operation.chain.append(test_link)
    loop.run_until_complete(BaseService.get_service('data_svc').store(test_operation))


@pytest.mark.usefixtures(
    "setup_operations_api_test"
)
class TestOperationsApi:
    async def test_get_operations(self, api_client, api_cookies):
        resp = await api_client.get('/api/v2/operations', cookies=api_cookies)
        operations_list = await resp.json()
        assert len(operations_list) == 1
        operation_dict = operations_list[0]
        assert operation_dict['name'] == 'My Test Operation'
        assert operation_dict['id'] == '123'

    async def test_unauthorized_get_operations(self, api_client):
        resp = await api_client.get('/api/v2/operations')
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_get_operation_by_id(self, api_client, api_cookies):
        resp = await api_client.get('/api/v2/operations/123', cookies=api_cookies)
        operation_dict = await resp.json()
        assert operation_dict['name'] == 'My Test Operation'
        assert operation_dict['id'] == '123'

    async def test_unauthorized_get_operation_by_id(self, api_client):
        resp = await api_client.get('/api/v2/operations/123')
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_get_operation_report(self, api_client, api_cookies, mocker, async_return):
        with mocker.patch('app.objects.c_operation.Operation.all_facts') as mock_all_facts:
            mock_all_facts.return_value = async_return([])
            test_objective = Objective(id='123', name='test objective', description='test', goals=[])
            BaseService.get_service('data_svc').ram['operations'][0].objective = test_objective
            resp = await api_client.get('/api/v2/operations/123/report', cookies=api_cookies)
            report = await resp.json()
            assert report['name'] == 'My Test Operation'
            assert report['jitter'] == '2/8'

    async def test_unauthorized_get_operation_report(self, api_client):
        resp = await api_client.get('/api/v2/operations/report')
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_create_operation(self, api_client, api_cookies):
        payload = dict(name='post_test', planner={'id': '123'},
                       adversary={'adversary_id': '123'}, source={'id': '123'})
        resp = await api_client.post('/api/v2/operations', cookies=api_cookies, json=payload)
        assert resp.status == HTTPStatus.OK
        op_data = await resp.json()
        assert op_data.get('name') == "post_test"
        op_exists = await BaseService.get_service('data_svc').locate('operations', {'name': 'post_test'})
        assert op_exists

    async def test_unauthorized_create_operation(self, api_client):
        payload = dict(name='post_test', planner={'id': '123'},
                       adversary={'adversary_id': '123'}, source={'id': '123'})
        resp = await api_client.post('/api/v2/operations', json=payload)
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_update_operation(self, api_client, api_cookies):
        payload = dict(state='running', obfuscator='base64')
        resp = await api_client.patch('/api/v2/operations/123', cookies=api_cookies, json=payload)
        assert resp.status == HTTPStatus.OK
        op = (await BaseService.get_service('data_svc').locate('operations', {'id': '123'}))[0]
        assert op.state == payload['state']
        assert op.obfuscator == payload['obfuscator']

    async def test_unauthorized_update_operation(self, api_client):
        payload = dict(state='running', obfuscator='base64')
        resp = await api_client.patch('/api/v2/operations/123', json=payload)
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_get_links(self, api_client, api_cookies):
        resp = await api_client.get('/api/v2/operations/123/links', cookies=api_cookies)
        assert resp.status == HTTPStatus.OK
        links = await resp.json()
        assert len(links) == 1

    async def test_unauthorized_get_links(self, api_client):
        resp = await api_client.get('/api/v2/operations/123/links')
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_get_operation_link(self, api_client, api_cookies):
        resp = await api_client.get('/api/v2/operations/123/links/456', cookies=api_cookies)
        assert resp.status == HTTPStatus.OK
        link = await resp.json()
        assert link
        assert link['command'] == 'd2hvYW1p'

    async def test_unauthorized_get_operation_link(self, api_client):
        resp = await api_client.get('/api/v2/operations/123/links/456')
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_update_operation_link(self, api_client, api_cookies):
        payload = dict(command='bHM=')
        resp = await api_client.patch('/api/v2/operations/123/links/456', cookies=api_cookies, json=payload)
        assert resp.status == HTTPStatus.OK
        op = (await BaseService.get_service('data_svc').locate('operations', {'id': '123'}))[0]
        assert op.chain[0].command == payload['command']

    async def test_unauthorized_update_operation_link(self, api_client):
        payload = dict(command='bHM=')
        resp = await api_client.patch('/api/v2/operations/123/links/456', json=payload)
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_get_potential_links(self, api_client, api_cookies, mocker, async_return):
        BaseService.get_service('rest_svc').build_potential_abilities = mocker.Mock()
        BaseService.get_service('rest_svc').build_potential_abilities.return_value = async_return([])
        test_link = Link(command='whoami', paw='123456', id='789')
        BaseService.get_service('rest_svc').build_potential_links = mocker.Mock()
        BaseService.get_service('rest_svc').build_potential_links.return_value = async_return([test_link])
        resp = await api_client.get('/api/v2/operations/123/potential-links', cookies=api_cookies)
        result = await resp.json()
        assert len(result) == 1
        assert result[0]['id'] == '789'

    async def test_unauthorized_get_potential_links(self, api_client):
        resp = await api_client.get('/api/v2/operations/123/potential-links')
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_get_potential_links_by_paw(self, api_client, api_cookies, mocker, async_return, ability, executor):
        BaseService.get_service('rest_svc').build_potential_abilities = mocker.Mock()
        BaseService.get_service('rest_svc').build_potential_abilities.return_value = async_return([])
        test_link = Link(command='whoami', paw='123456', id='789')
        BaseService.get_service('rest_svc').build_potential_links = mocker.Mock()
        BaseService.get_service('rest_svc').build_potential_links.return_value = async_return([test_link])
        resp = await api_client.get('/api/v2/operations/123/potential-links/123', cookies=api_cookies)
        result = await resp.json()
        assert len(result) == 1
        assert result[0]['id'] == '789'

    async def test_unauthorized_get_potential_links_by_paw(self, api_client):
        resp = await api_client.get('/api/v2/operations/123/potential-links/123')
        assert resp.status == HTTPStatus.UNAUTHORIZED

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
            assert result['ability']
            assert result['executor']

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
