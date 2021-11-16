import pytest

from http import HTTPStatus

from app.objects.c_ability import AbilitySchema
from app.objects.c_operation import OperationSchema
from app.objects.c_adversary import AdversarySchema
from app.objects.c_schedule import ScheduleSchema
from app.objects.c_agent import Agent
from app.objects.c_objective import Objective
from app.objects.c_planner import PlannerSchema
from app.objects.c_source import Source, SourceSchema
from app.objects.secondclass.c_executor import ExecutorSchema
from app.objects.secondclass.c_fact import Fact
from app.objects.secondclass.c_relationship import Relationship
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
def test_source_existing_relationships(loop):
    test_fact_1 = Fact(trait='test_1', value='1')
    test_fact_2 = Fact(trait='test_2', value='2')
    test_relationship = Relationship(source=test_fact_1, edge='test_edge', target=test_fact_2)
    test_source = Source(id='123', name='test', facts=[test_fact_1, test_fact_2], adjustments=[],
                         relationships=[test_relationship])
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
    return ExecutorSchema().load(dict(timeout=60, platform=test_agent.platform, name='linux', command='ls'))


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
def test_schedule(test_operation, loop, mock_time):
    schedule = ScheduleSchema().load(dict(name='123',
                                          schedule=mock_time,
                                          task=test_operation))
    loop.run_until_complete(BaseService.get_service('data_svc').store(schedule))
    return schedule


@pytest.fixture
def setup_finished_operation(loop, test_operation):
    finished_operation = OperationSchema().load(test_operation)
    finished_operation.id = '000'
    finished_operation.state = 'finished'
    loop.run_until_complete(BaseService.get_service('data_svc').store(finished_operation))


@pytest.fixture
def setup_operations_api_test(loop, api_v2_client, test_operation, test_agent, test_ability):
    test_operation = OperationSchema().load(test_operation)
    test_operation.agents.append(test_agent)
    test_operation.set_start_details()
    test_objective = Objective(id='123', name='test objective', description='test', goals=[])
    test_operation.objective = test_objective
    loop.run_until_complete(BaseService.get_service('data_svc').store(test_operation))


@pytest.mark.usefixtures(
    "setup_operations_api_test"
)
class TestOperationsApi:
    async def test_get_schedules(self, api_v2_client, api_cookies, test_schedule):
        resp = await api_v2_client.get('/api/v2/schedules', cookies=api_cookies)
        schedules_list = await resp.json()
        assert len(schedules_list) == 1
        schedule_dict = schedules_list[0]
        assert schedule_dict == ScheduleSchema().dump(test_schedule)

    async def test_unauthorized_get_schedules(self, api_v2_client):
        resp = await api_v2_client.get('/api/v2/schedules')
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_get_schedule_by_id(self, api_v2_client, api_cookies, test_schedule):
        resp = await api_v2_client.get('/api/v2/schedules/123', cookies=api_cookies)
        schedule_dict = await resp.json()
        assert schedule_dict == ScheduleSchema().dump(test_schedule)

    async def test_unauthorized_get_schedule_by_id(self, api_v2_client):
        resp = await api_v2_client.get('/api/v2/schedules/123')
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_nonexistent_schedule_get_schedule_by_id(self, api_v2_client, api_cookies):
        resp = await api_v2_client.get('/api/v2/schedules/999', cookies=api_cookies)
        assert resp.status == HTTPStatus.NOT_FOUND

    async def test_create_schedule(self, api_v2_client, api_cookies):
        payload = dict(name='post_test', planner={'id': '123'},
                       adversary={'adversary_id': '123', 'name': 'ad-hoc'}, source={'id': '123'})
        resp = await api_v2_client.post('/api/v2/schedules', cookies=api_cookies, json=payload)
        assert resp.status == HTTPStatus.OK
        op_exists = await BaseService.get_service('data_svc').locate('schedules', {'name': 'post_test'})
        assert op_exists
        op_data = await resp.json()
        assert op_data['name'] == payload['name']
        assert op_data['start']
        assert op_data['planner']['id'] == payload['planner']['id']
        assert op_data['adversary']['name'] == payload['adversary']['name']
        assert op_data['source']['id'] == payload['source']['id']

    async def test_duplicate_create_schedule(self, api_v2_client, api_cookies, test_schedule):
        payload = dict(name='post_test', id=test_schedule['id'], planner={'id': '123'},
                       adversary={'adversary_id': '123'}, source={'id': '123'})
        resp = await api_v2_client.post('/api/v2/schedules', cookies=api_cookies, json=payload)
        assert resp.status == HTTPStatus.BAD_REQUEST

    async def test_unauthorized_create_schedule(self, api_v2_client):
        payload = dict(name='post_test', planner={'id': '123'},
                       adversary={'adversary_id': '123'}, source={'id': '123'})
        resp = await api_v2_client.post('/api/v2/schedules', json=payload)
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_update_schedule(self, api_v2_client, api_cookies, mocker, async_return, test_operation):
        op_manager_path = 'app.api.v2.managers.operation_api_manager.OperationApiManager.validate_schedule_state'
        with mocker.patch(op_manager_path) as mock_validate:
            mock_validate.return_value = async_return(True)
            payload = dict(state='running', obfuscator='base64')
            resp = await api_v2_client.patch('/api/v2/schedules/123', cookies=api_cookies, json=payload)
            assert resp.status == HTTPStatus.OK
            op = (await BaseService.get_service('data_svc').locate('schedules', {'id': '123'}))[0]
            assert op.state == payload['state']
            assert op.obfuscator == payload['obfuscator']
            assert op.id == test_schedule['id']
            assert op.name == test_schedule['name']
            assert op.planner.planner_id == test_schedule['planner']['id']

    async def test_unauthorized_update_schedule(self, api_v2_client):
        payload = dict(state='running', obfuscator='base64')
        resp = await api_v2_client.patch('/api/v2/schedules/123', json=payload)
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_nonexistent_schedule_update(self, api_v2_client, api_cookies):
        payload = dict(state='running', obfuscator='base64')
        resp = await api_v2_client.patch('/api/v2/schedules/999', json=payload, cookies=api_cookies)
        assert resp.status == HTTPStatus.NOT_FOUND

    async def test_update_finished_schedule(self, api_v2_client, api_cookies, setup_finished_operation):
        payload = dict(state='running', obfuscator='base64')
        resp = await api_v2_client.patch('/api/v2/schedules/000', cookies=api_cookies, json=payload)
        assert resp.status == HTTPStatus.BAD_REQUEST
