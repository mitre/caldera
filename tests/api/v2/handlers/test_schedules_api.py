import pytest

from http import HTTPStatus
from unittest import mock

from app.objects.c_operation import OperationSchema
from app.objects.c_schedule import ScheduleSchema
from app.utility.base_service import BaseService


@pytest.fixture
def updated_schedule_payload():
    payload = {
        'schedule': '0 1 * * *',
        'task': {
            'autonomous': 1,
            'obfuscator': 'base64',
            'state': 'running'
        }
    }
    return payload


@pytest.fixture
def expected_updated_schedule_dump(test_schedule, updated_schedule_payload):
    test_schedule_dump = test_schedule.schema.dump(test_schedule)

    def _merge_dictionaries(dict1, dict2):
        for key in dict1.keys():
            if isinstance(dict1[key], dict):
                _merge_dictionaries(dict1[key], dict2[key])
            else:
                dict2[key] = dict1[key]
        return dict2
    expected_dict = _merge_dictionaries(updated_schedule_payload, test_schedule_dump)
    schedule = ScheduleSchema().load(expected_dict)
    return schedule.schema.dump(schedule)


@pytest.fixture
def replaced_schedule_payload():
    payload = {
        'schedule': '0 12 12 * *',
        'task': {
            'autonomous': 1,
            'obfuscator': 'base64',
            'state': 'running',
            'name': 'replaced_op',
            'planner': {'id': '123'},
            'adversary': {'adversary_id': '123', 'name': 'ad-hoc'},
            'source': {'id': '123'}
        },
        'id': '123'
    }
    return payload


@pytest.fixture
def new_schedule_payload(test_planner, test_adversary, test_source):
    payload = dict(schedule='0 0 * * *',
                   id='456',
                   task={
                       'name': 'new_scheduled_operation',
                       'planner': test_planner.schema.dump(test_planner),
                       'adversary': test_adversary.schema.dump(test_adversary),
                       'source': test_source.schema.dump(test_source)
                   })
    return payload


@pytest.fixture
def expected_new_schedule_dump(new_schedule_payload):
    schedule = ScheduleSchema().load(new_schedule_payload)
    dump = schedule.schema.dump(schedule)
    dump['task']['id'] = mock.ANY
    return dump


@pytest.fixture
def test_schedule(test_operation, event_loop):
    operation = OperationSchema().load(test_operation)
    schedule = ScheduleSchema().load(dict(id='123',
                                          schedule='0 3 * * *',
                                          task=operation.schema.dump(operation)))
    event_loop.run_until_complete(BaseService.get_service('data_svc').store(schedule))
    return schedule


@pytest.mark.usefixtures(
    "setup_operations_api_test"
)
class TestSchedulesApi:
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
        resp = await api_v2_client.get(f'/api/v2/schedules/{test_schedule.id}', cookies=api_cookies)
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
                                                                           {'id': expected_new_schedule_dump['id']})
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
        resp = await api_v2_client.patch(f'/api/v2/schedules/{expected_updated_schedule_dump["id"]}',
                                         cookies=api_cookies, json=updated_schedule_payload)
        assert resp.status == HTTPStatus.OK
        returned_schedule_data = await resp.json()
        stored_schedule = (await BaseService.get_service('data_svc').locate('schedules',
                                                                            {'id': '123'}))[0]
        assert stored_schedule.schema.dump(stored_schedule) == expected_updated_schedule_dump
        assert returned_schedule_data == expected_updated_schedule_dump

    async def test_unauthorized_update_schedule(self, api_v2_client, updated_schedule_payload):
        resp = await api_v2_client.patch('/api/v2/schedules/123', json=updated_schedule_payload)
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_nonexistent_schedule_update(self, api_v2_client, api_cookies, updated_schedule_payload):
        resp = await api_v2_client.patch('/api/v2/schedules/999', json=updated_schedule_payload, cookies=api_cookies)
        assert resp.status == HTTPStatus.NOT_FOUND

    async def test_replace_schedule(self, api_v2_client, api_cookies, test_schedule, replaced_schedule_payload):
        resp = await api_v2_client.put('/api/v2/schedules/123', cookies=api_cookies, json=replaced_schedule_payload)
        assert resp.status == HTTPStatus.OK
        returned_schedule_data = await resp.json()
        stored_schedule = await BaseService.get_service('data_svc').locate('schedules',
                                                                           {'id': replaced_schedule_payload['id']})
        stored_schedule = stored_schedule[0].schema.dump(stored_schedule[0])
        assert returned_schedule_data == stored_schedule
        returned_task = returned_schedule_data['task']
        assert returned_task['planner']['id'] == replaced_schedule_payload['task']['planner']['id']
        assert returned_task['adversary']['name'] == replaced_schedule_payload['task']['adversary']['name']
        assert returned_task['source']['id'] == replaced_schedule_payload['task']['source']['id']

    async def test_unauthorized_replace_schedule(self, api_v2_client, test_schedule, updated_schedule_payload):
        resp = await api_v2_client.put('/api/v2/schedules/123', json=updated_schedule_payload)
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_replace_nonexistent_schedule(self, api_v2_client, api_cookies, new_schedule_payload,
                                                expected_new_schedule_dump):
        resp = await api_v2_client.put(f'/api/v2/schedules/{expected_new_schedule_dump["id"]}',
                                       cookies=api_cookies, json=new_schedule_payload)
        assert resp.status == HTTPStatus.OK
        returned_schedule_data = await resp.json()
        stored_schedule = await BaseService.get_service('data_svc').locate('schedules',
                                                                           {'id': expected_new_schedule_dump['id']})
        stored_schedule = stored_schedule[0].schema.dump(stored_schedule[0])
        assert returned_schedule_data == stored_schedule
        assert returned_schedule_data == expected_new_schedule_dump
