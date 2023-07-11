import pytest

from http import HTTPStatus

from app.objects.c_adversary import AdversarySchema, Adversary
from app.utility.base_service import BaseService


@pytest.fixture
def updated_adversary_payload():
    return {
        'name': 'test updated adversary',
        'description': 'an updated adversary',
        'objective': '00000000-0000-0000-0000-000000000000',
        'tags': ['test tag'],
        'atomic_ordering': ['123']
    }


@pytest.fixture
def invalid_updated_adversary_payload(updated_adversary_payload):
    payload = updated_adversary_payload.copy()
    payload['id'] = '000'
    return payload


@pytest.fixture
def expected_updated_adversary_dump(test_adversary, updated_adversary_payload):
    adversary_dict = test_adversary.schema.dump(test_adversary)
    adversary_dict.update(updated_adversary_payload)
    return adversary_dict


@pytest.fixture
def new_adversary_payload():
    return {
        'name': 'test new adversary',
        'description': 'a new adversary',
        'adversary_id': '456',
        'objective': '495a9828-cab1-44dd-a0ca-66e58177d8cc',
        'tags': [],
        'atomic_ordering': [],
        'plugin': ''
    }


@pytest.fixture
def expected_new_adversary_dump(new_adversary_payload):
    adversary = Adversary.load(new_adversary_payload)
    return adversary.schema.dump(adversary)


@pytest.fixture
def new_adversary_duplicate_id_payload():
    return {
        'name': 'test new adversary',
        'description': 'a new adversary with an invalid payload',
        'adversary_id': '456',
        'id': '000',
        'objective': '495a9828-cab1-44dd-a0ca-66e58177d8cc',
        'tags': [],
        'atomic_ordering': [],
        'plugin': ''
    }


@pytest.fixture
def expected_new_duplicate_id_adversary_dump(new_adversary_duplicate_id_payload):
    payload = new_adversary_duplicate_id_payload.copy()
    payload.pop('id')
    adversary = Adversary.load(payload)
    return adversary.schema.dump(adversary)


@pytest.fixture
def test_adversary(event_loop):
    expected_adversary = {'name': 'test',
                          'description': 'an empty adversary profile',
                          'adversary_id': '123',
                          'objective': '495a9828-cab1-44dd-a0ca-66e58177d8cc',
                          'tags': [],
                          'atomic_ordering': [],
                          'plugin': ''}
    test_adversary = AdversarySchema().load(expected_adversary)
    event_loop.run_until_complete(BaseService.get_service('data_svc').store(test_adversary))
    return test_adversary


class TestAdversariesApi:
    async def test_get_adversaries(self, api_v2_client, api_cookies, test_adversary):
        resp = await api_v2_client.get('/api/v2/adversaries', cookies=api_cookies)
        assert resp.status == HTTPStatus.OK
        output = await resp.json()
        assert len(output) == 1
        adversary_dict = output[0]
        assert adversary_dict == test_adversary.schema.dump(test_adversary)

    async def test_unauthorized_get_adversaries(self, api_v2_client, test_adversary):
        resp = await api_v2_client.get('/api/v2/adversaries')
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_get_adversary_by_id(self, api_v2_client, api_cookies, test_adversary):
        resp = await api_v2_client.get('/api/v2/adversaries/123', cookies=api_cookies)
        assert resp.status == HTTPStatus.OK
        output = await resp.json()
        assert output == test_adversary.schema.dump(test_adversary)

    async def test_unauthorized_get_adversary_by_id(self, api_v2_client, test_adversary):
        resp = await api_v2_client.get('/api/v2/adversaries/123')
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_get_nonexistent_adversary_by_id(self, api_v2_client, api_cookies, test_adversary):
        resp = await api_v2_client.get('/api/v2/adversaries/999', cookies=api_cookies)
        assert resp.status == HTTPStatus.NOT_FOUND

    async def test_create_adversary(self, api_v2_client, api_cookies, test_adversary, new_adversary_payload,
                                    expected_new_adversary_dump):
        resp = await api_v2_client.post('/api/v2/adversaries', cookies=api_cookies, json=new_adversary_payload)
        assert resp.status == HTTPStatus.OK
        output = await resp.json()
        assert await BaseService.get_service('data_svc').locate('adversaries',
                                                                match={'adversary_id': output['adversary_id']})
        assert output == expected_new_adversary_dump

    async def test_create_adversary_with_invalid_payload(self, api_v2_client, api_cookies, test_adversary,
                                                         new_adversary_duplicate_id_payload,
                                                         expected_new_duplicate_id_adversary_dump):
        resp = await api_v2_client.post('/api/v2/adversaries', cookies=api_cookies,
                                        json=new_adversary_duplicate_id_payload)
        assert resp.status == HTTPStatus.OK
        invalid_id = new_adversary_duplicate_id_payload['id']
        assert not (await BaseService.get_service('data_svc').locate('adversaries',
                                                                     match={'adversary_id': invalid_id}))
        output = await resp.json()
        assert await BaseService.get_service('data_svc').locate('adversaries',
                                                                match={'adversary_id': output['adversary_id']})
        assert output == expected_new_duplicate_id_adversary_dump

    async def test_unauthorized_create_adversary(self, api_v2_client, test_adversary, new_adversary_payload):
        resp = await api_v2_client.post('/api/v2/adversaries', json=new_adversary_payload)
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_create_duplicate_adversary(self, api_v2_client, api_cookies, test_adversary, new_adversary_payload):
        new_adversary_payload['adversary_id'] = test_adversary.adversary_id
        resp = await api_v2_client.post('/api/v2/adversaries', cookies=api_cookies, json=new_adversary_payload)
        assert resp.status == HTTPStatus.BAD_REQUEST

    async def test_update_adversary(self, api_v2_client, api_cookies, test_adversary, updated_adversary_payload,
                                    mocker, expected_updated_adversary_dump):
        with mocker.patch('app.api.v2.managers.adversary_api_manager.AdversaryApiManager.strip_yml') as mock_strip_yml:
            mock_strip_yml.return_value = [test_adversary.schema.dump(test_adversary)]
            with mocker.patch('app.objects.c_adversary.Adversary.verify') as mock_verify:
                mock_verify.return_value = None
                resp = await api_v2_client.patch('/api/v2/adversaries/123', cookies=api_cookies,
                                                 json=updated_adversary_payload)
                assert resp.status == HTTPStatus.OK
                output = await resp.json()
                assert output == expected_updated_adversary_dump

    async def test_update_adversary_invalid_payload(self, api_v2_client, api_cookies, test_adversary,
                                                    updated_adversary_payload, invalid_updated_adversary_payload,
                                                    mocker, expected_updated_adversary_dump):
        with mocker.patch('app.api.v2.managers.adversary_api_manager.AdversaryApiManager.strip_yml') as mock_strip_yml:
            mock_strip_yml.return_value = [test_adversary.schema.dump(test_adversary)]
            with mocker.patch('app.objects.c_adversary.Adversary.verify') as mock_verify:
                mock_verify.return_value = None
                resp = await api_v2_client.patch(f'/api/v2/adversaries/{test_adversary.adversary_id}',
                                                 cookies=api_cookies, json=invalid_updated_adversary_payload)
                assert resp.status == HTTPStatus.OK
                output = await resp.json()
                assert output == expected_updated_adversary_dump
                invalid_id = invalid_updated_adversary_payload['id']
                assert not (await BaseService.get_service('data_svc').locate('adversaries',
                                                                             match={'adversary_id': invalid_id}))

    async def test_unauthorized_update_adversary(self, api_v2_client, test_adversary, updated_adversary_payload):
        resp = await api_v2_client.patch('/api/v2/adversaries/123', json=updated_adversary_payload)
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_update_nonexistent_adversary(self, api_v2_client, api_cookies, updated_adversary_payload):
        resp = await api_v2_client.patch('/api/v2/adversaries/999', json=updated_adversary_payload)
        assert resp.status == HTTPStatus.NOT_FOUND

    async def test_create_or_update_existing_adversary(self, api_v2_client, api_cookies, test_adversary, mocker,
                                                       updated_adversary_payload, expected_updated_adversary_dump):
        with mocker.patch('app.objects.c_adversary.Adversary.verify') as mock_verify:
            mock_verify.return_value = None
            resp = await api_v2_client.put('/api/v2/adversaries/123', cookies=api_cookies,
                                           json=updated_adversary_payload)
            assert resp.status == HTTPStatus.OK
            output = await resp.json()
            assert output == expected_updated_adversary_dump

    async def test_create_or_update_adversary_with_invalid_payload(self, api_v2_client, api_cookies, mocker,
                                                                   new_adversary_duplicate_id_payload,
                                                                   expected_new_duplicate_id_adversary_dump):
        with mocker.patch('app.objects.c_adversary.Adversary.verify') as mock_verify:
            mock_verify.return_value = None
            valid_id = new_adversary_duplicate_id_payload.get('adversary_id')
            invalid_id = new_adversary_duplicate_id_payload.get('id')
            resp = await api_v2_client.put(f'/api/v2/adversaries/{valid_id}', cookies=api_cookies,
                                           json=new_adversary_duplicate_id_payload)
            assert resp.status == HTTPStatus.OK
            output = await resp.json()
            assert output == expected_new_duplicate_id_adversary_dump
            assert not (await BaseService.get_service('data_svc').locate('adversaries',
                                                                         match={'adversary_id': invalid_id}))

    async def test_unauthorized_create_or_update_adversary(self, api_v2_client, test_adversary, new_adversary_payload):
        resp = await api_v2_client.put('/api/v2/adversaries/123', json=new_adversary_payload)
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_create_or_update_nonexistent_adversary(self, api_v2_client, api_cookies, test_adversary,
                                                          new_adversary_payload, expected_new_adversary_dump):
        resp = await api_v2_client.put('/api/v2/adversaries/456', cookies=api_cookies, json=new_adversary_payload)
        assert resp.status == HTTPStatus.OK
        output = await resp.json()
        assert await BaseService.get_service('data_svc').locate('adversaries',
                                                                match={'adversary_id': output['adversary_id']})
        assert output == expected_new_adversary_dump
