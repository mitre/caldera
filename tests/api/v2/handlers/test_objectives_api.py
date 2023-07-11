import pytest

from http import HTTPStatus

from app.objects.c_objective import Objective, ObjectiveSchema
from app.objects.secondclass.c_goal import Goal
from app.utility.base_service import BaseService


@pytest.fixture
def new_objective_payload():
    test_goal = Goal(target='new goal', value='in_progress')
    return {
        'id': '456',
        'name': 'new test objective',
        'description': 'a new test objective',
        'goals': [test_goal.schema.dump(test_goal)]
    }


@pytest.fixture
def expected_new_objective_dump(new_objective_payload):
    objective = ObjectiveSchema().load(new_objective_payload)
    return objective.schema.dump(objective)


@pytest.fixture
def updated_objective_payload(test_objective, test_goal):
    objective_data = test_objective.schema.dump(test_objective)
    updated_goal = Goal(target='updated target', value='complete')
    objective_data.update(dict(name='an updated test objective',
                               description='a test objective that has been updated',
                               goals=[updated_goal.schema.dump(updated_goal)]))
    return objective_data


@pytest.fixture
def replaced_objective_payload(test_objective):
    objective_data = test_objective.schema.dump(test_objective)
    test_goal = Goal(target='replaced target', value='in_progress')
    objective_data.update(dict(name='replaced test objective',
                               description='a test objective that has been replaced',
                               goals=[test_goal.schema.dump(test_goal)]))
    return objective_data


@pytest.fixture
def test_goal():
    return Goal(target='test target', value='in_progress')


@pytest.fixture
def test_objective(event_loop, test_goal):
    objective = Objective(id='123', name='test objective', description='a test objective', goals=[test_goal])
    event_loop.run_until_complete(BaseService.get_service('data_svc').store(objective))
    return objective


@pytest.fixture
def expected_test_objective_dump(test_objective):
    return test_objective.schema.dump(test_objective)


class TestObjectivesApi:
    async def test_get_objectives(self, api_v2_client, api_cookies, test_objective, expected_test_objective_dump):
        resp = await api_v2_client.get('/api/v2/objectives', cookies=api_cookies)
        objectives_list = await resp.json()
        assert len(objectives_list) == 1
        objective_dict = objectives_list[0]
        assert objective_dict == expected_test_objective_dump

    async def test_unauthorized_get_objectives(self, api_v2_client, test_objective):
        resp = await api_v2_client.get('/api/v2/objectives')
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_get_objective_by_id(self, api_v2_client, api_cookies, test_objective, expected_test_objective_dump):
        resp = await api_v2_client.get('/api/v2/objectives/123', cookies=api_cookies)
        objective_dict = await resp.json()
        assert objective_dict == expected_test_objective_dump

    async def test_unauthorized_get_objective_by_id(self, api_v2_client, test_objective):
        resp = await api_v2_client.get('/api/v2/objectives/123')
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_get_nonexistent_objective_by_id(self, api_v2_client, api_cookies):
        resp = await api_v2_client.get('/api/v2/objectives/999', cookies=api_cookies)
        assert resp.status == HTTPStatus.NOT_FOUND

    async def test_create_objective(self, api_v2_client, api_cookies, new_objective_payload,
                                    expected_new_objective_dump):
        resp = await api_v2_client.post('/api/v2/objectives', cookies=api_cookies, json=new_objective_payload)
        assert resp.status == HTTPStatus.OK
        objective_data = await resp.json()
        assert objective_data == expected_new_objective_dump
        stored_objective = (await BaseService.get_service('data_svc').locate('objectives', {'id': '456'}))[0]
        assert stored_objective.schema.dump(stored_objective) == expected_new_objective_dump

    async def test_unauthorized_create_objective(self, api_v2_client, new_objective_payload):
        resp = await api_v2_client.post('/api/v2/objectives', json=new_objective_payload)
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_create_duplicate_objective(self, api_v2_client, api_cookies, test_objective):
        payload = test_objective.schema.dump(test_objective)
        resp = await api_v2_client.post('/api/v2/objectives', cookies=api_cookies, json=payload)
        assert resp.status == HTTPStatus.BAD_REQUEST

    async def test_update_objective(self, api_v2_client, api_cookies, test_objective, updated_objective_payload,
                                    mocker):
        with mocker.patch('app.api.v2.managers.base_api_manager.BaseApiManager.strip_yml') as mock_strip_yml:
            mock_strip_yml.return_value = [test_objective.schema.dump(test_objective)]
            resp = await api_v2_client.patch('/api/v2/objectives/123', cookies=api_cookies,
                                             json=updated_objective_payload)
            assert resp.status == HTTPStatus.OK
            objective = await resp.json()
            assert objective == updated_objective_payload
            stored_objective = (await BaseService.get_service('data_svc').locate('objectives', {'id': '123'}))[0]
            assert stored_objective.schema.dump(stored_objective) == updated_objective_payload

    async def test_unauthorized_update_objective(self, api_v2_client, test_objective, updated_objective_payload):
        resp = await api_v2_client.patch('/api/v2/objectives/123', json=updated_objective_payload)
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_update_nonexistent_objective(self, api_v2_client, api_cookies, updated_objective_payload):
        resp = await api_v2_client.patch('/api/v2/objectives/999', cookies=api_cookies, json=updated_objective_payload)
        assert resp.status == HTTPStatus.NOT_FOUND

    async def test_replace_objective(self, api_v2_client, api_cookies, test_objective, replaced_objective_payload):
        resp = await api_v2_client.put('/api/v2/objectives/123', cookies=api_cookies, json=replaced_objective_payload)
        assert resp.status == HTTPStatus.OK
        objective = await resp.json()
        assert objective == replaced_objective_payload
        stored_objective = (await BaseService.get_service('data_svc').locate('objectives', {'id': '123'}))[0]
        assert stored_objective.schema.dump(stored_objective) == replaced_objective_payload

    async def test_unauthorized_replace_objective(self, api_v2_client, test_objective, replaced_objective_payload):
        resp = await api_v2_client.put('/api/v2/objectives/123', json=replaced_objective_payload)
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_replace_nonexistent_objective(self, api_v2_client, api_cookies, new_objective_payload,
                                                 expected_new_objective_dump):
        resp = await api_v2_client.put('/api/v2/objectives/456', cookies=api_cookies, json=new_objective_payload)
        assert resp.status == HTTPStatus.OK
        objective = await resp.json()
        assert objective == expected_new_objective_dump
        stored_objective = (await BaseService.get_service('data_svc').locate('objectives', {'id': '456'}))[0]
        assert stored_objective.schema.dump(stored_objective) == expected_new_objective_dump
