import pytest

from http import HTTPStatus
from unittest import mock

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
def updated_schedule_payload(test_schedule):
    payload = test_schedule.schema.dump(test_schedule)
    payload['schedule'] = '01:00:00.000000'
    return payload


@pytest.fixture
def expected_updated_schedule_dump(updated_schedule_payload):
    schedule = ScheduleSchema().load(updated_schedule_payload)
    return schedule.schema.dump(schedule)


@pytest.fixture
def new_schedule_payload():
    payload = dict(name='post_test',
                   schedule='00:00:00.000000',
                   task={
                       'name': 'new_operation',
                       'planner': {'id': '123'},
                       'adversary': {'adversary_id': '123', 'name': 'ad-hoc'},
                       'source': {'id': '123'}
                   })
    return payload


@pytest.fixture
def expected_new_schedule_dump(new_schedule_payload):
    schedule = ScheduleSchema().load(new_schedule_payload)
    dump = schedule.schema.dump(schedule)
    dump['task']['id'] = mock.ANY
    return dump


@pytest.fixture
def test_schedule(test_operation, loop):
    operation = OperationSchema().load(test_operation)
    schedule = ScheduleSchema().load(dict(name='123',
                                          schedule='03:00:00.000000',
                                          task=operation.schema.dump(operation)))
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

    async def test_create_schedule(self, api_v2_client, api_cookies, new_schedule_payload, expected_new_schedule_dump):
        resp = await api_v2_client.post('/api/v2/schedules', cookies=api_cookies, json=new_schedule_payload)
        assert resp.status == HTTPStatus.OK
        schedule_exists = await BaseService.get_service('data_svc').locate('schedules',
                                                                           {'name': new_schedule_payload['name']})
        assert schedule_exists
        stored_schedule = schedule_exists[0]
        returned_schedule_data = await resp.json()
        assert returned_schedule_data == stored_schedule.schema.dump(stored_schedule)
        assert returned_schedule_data == expected_new_schedule_dump

    async def test_duplicate_create_schedule(self, api_v2_client, api_cookies, test_schedule):
        payload = test_schedule.schema.dump(test_schedule)
        resp = await api_v2_client.post('/api/v2/schedules', cookies=api_cookies, json=payload)
        assert resp.status == HTTPStatus.BAD_REQUEST

    async def test_unauthorized_create_schedule(self, api_v2_client, new_schedule_payload):
        resp = await api_v2_client.post('/api/v2/schedules', json=new_schedule_payload)
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_update_schedule(self, api_v2_client, api_cookies, mocker, async_return, updated_schedule_payload,
                                   expected_updated_schedule_dump):
        resp = await api_v2_client.patch('/api/v2/schedules/123', cookies=api_cookies, json=updated_schedule_payload)
        assert resp.status == HTTPStatus.OK
        returned_schedule_data = await resp.json()
        stored_schedule = (await BaseService.get_service('data_svc').locate('schedules',
                                                                            {'name': updated_schedule_payload['name']}))[0]
        assert stored_schedule.schema.dump(stored_schedule) == expected_updated_schedule_dump
        assert returned_schedule_data == expected_updated_schedule_dump

    async def test_unauthorized_update_schedule(self, api_v2_client, updated_schedule_payload):
        resp = await api_v2_client.patch('/api/v2/schedules/123', json=updated_schedule_payload)
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_nonexistent_schedule_update(self, api_v2_client, api_cookies, updated_schedule_payload):
        resp = await api_v2_client.patch('/api/v2/schedules/999', json=updated_schedule_payload, cookies=api_cookies)
        assert resp.status == HTTPStatus.NOT_FOUND

    async def test_replace_schedule(self, api_v2_client, api_cookies, test_schedule, updated_schedule_payload,
                                    expected_updated_schedule_dump):
        resp = await api_v2_client.put('/api/v2/schedules/123', cookies=api_cookies, json=updated_schedule_payload)
        assert resp.status == HTTPStatus.OK
        returned_schedule_data = await resp.json()
        stored_schedule = await BaseService.get_service('data_svc').locate('schedules',
                                                                           {'name': updated_schedule_payload['name']})
        stored_schedule = stored_schedule[0].schema.dump(stored_schedule[0])
        assert returned_schedule_data == stored_schedule
        assert returned_schedule_data == expected_updated_schedule_dump

    async def test_unauthorized_replace_schedule(self, api_v2_client, test_schedule, updated_schedule_payload):
        resp = await api_v2_client.put('/api/v2/schedules/123', json=updated_schedule_payload)
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_replace_nonexistent_schedule(self, api_v2_client, api_cookies, new_schedule_payload,
                                                expected_new_schedule_dump):
        resp = await api_v2_client.put(f'/api/v2/schedules/{new_schedule_payload["name"]}',
                                       cookies=api_cookies, json=new_schedule_payload)
        assert resp.status == HTTPStatus.OK
        returned_schedule_data = await resp.json()
        stored_schedule = await BaseService.get_service('data_svc').locate('schedules',
                                                                           {'name': expected_new_schedule_dump['name']})
        stored_schedule = stored_schedule[0].schema.dump(stored_schedule[0])
        assert returned_schedule_data == stored_schedule
        assert returned_schedule_data == expected_new_schedule_dump
