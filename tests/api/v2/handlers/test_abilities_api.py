import pytest

from http import HTTPStatus

from app.objects.c_ability import Ability
from app.objects.secondclass.c_executor import Executor, ExecutorSchema
from app.utility.base_service import BaseService


@pytest.fixture
def test_ability(loop, api_client, executor):
    executor_linux = executor(name='sh', platform='linux')
    ability = Ability(ability_id='123', name='Test Ability', executors=[executor_linux],
                      technique_name='collection', technique_id='1')
    loop.run_until_complete(BaseService.get_service('data_svc').store(ability))
    return ability


class TestAbilitiesApi:
    async def test_get_abilities(self, api_client, api_cookies, test_ability):
        resp = await api_client.get('/api/v2/abilities', cookies=api_cookies)
        abilities_list = await resp.json()
        assert len(abilities_list) == 1
        ability_dict = abilities_list[0]
        assert ability_dict['ability_id'] == test_ability.ability_id
        assert ability_dict['name'] == test_ability.name
        assert ability_dict['technique_name'] == test_ability.technique_name
        assert len(ability_dict['executors']) == 1

    async def test_unauthorized_get_abilities(self, api_client, test_ability):
        resp = await api_client.get('/api/v2/abilities')
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_get_ability_by_id(self, api_client, api_cookies, test_ability):
        resp = await api_client.get('/api/v2/abilities/123', cookies=api_cookies)
        ability_dict = await resp.json()
        assert ability_dict['ability_id'] == test_ability.ability_id
        assert ability_dict['name'] == test_ability.name
        assert ability_dict['technique_name'] == test_ability.technique_name
        assert len(ability_dict['executors']) == 1

    async def test_unauthorized_get_ability_by_id(self, api_client, test_ability):
        resp = await api_client.get('/api/v2/abilities/123')
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_get_nonexistent_ability_by_id(self, api_client, api_cookies):
        resp = await api_client.get('/api/v2/abilities/999', cookies=api_cookies)
        assert resp.status == HTTPStatus.NOT_FOUND

    async def test_create_ability(self, api_client, api_cookies, mocker, async_return):
        test_executor_linux = Executor(name='sh', platform='linux', command='whoami')
        payload = dict(name='new test ability', ability_id='456', tactic='collection', technique_name='collection',
                       technique_id='1', executors=[ExecutorSchema().dump(test_executor_linux)])
        resp = await api_client.post('/api/v2/abilities', cookies=api_cookies, json=payload)
        assert resp.status == HTTPStatus.OK
        ability_data = await resp.json()
        assert ability_data.get('name') == payload['name']
        assert ability_data.get('ability_id') == payload['ability_id']
        assert ability_data.get('tactic') == payload['tactic']
        ability_exists = await BaseService.get_service('data_svc').locate('abilities', {'ability_id': '456'})
        assert ability_exists

    async def test_unauthorized_create_ability(self, api_client):
        test_executor_linux = Executor(name='sh', platform='linux', command='whoami')
        payload = dict(name='new test ability', ability_id='456', tactic='collection', technique_name='collection',
                       technique_id='1', executors=[ExecutorSchema().dump(test_executor_linux)])
        resp = await api_client.post('/api/v2/abilities', json=payload)
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_create_duplicate_ability(self, api_client, api_cookies, mocker, async_return, test_ability):
        test_executor_linux = Executor(name='sh', platform='linux', command='whoami')
        payload = dict(name='new test ability', ability_id='123', tactic='collection', technique_name='collection',
                       technique_id='1', executors=[ExecutorSchema().dump(test_executor_linux)])
        resp = await api_client.post('/api/v2/abilities', cookies=api_cookies, json=payload)
        assert resp.status == HTTPStatus.BAD_REQUEST

    async def test_create_invalid_ability(self, api_client, api_cookies, mocker, async_return, test_ability):
        payload = dict(name='new test ability', ability_id='123', technique_name='collection',
                       technique_id='1', executors=[])
        resp = await api_client.post('/api/v2/abilities', cookies=api_cookies, json=payload)
        assert resp.status == HTTPStatus.BAD_REQUEST

    async def test_update_ability(self, api_client, api_cookies, test_ability):
        payload = dict(name='an updated test ability', tactic='defense-evasion')
        resp = await api_client.patch('/api/v2/abilities/123', cookies=api_cookies, json=payload)
        assert resp.status == HTTPStatus.OK
        ability = (await BaseService.get_service('data_svc').locate('abilities', {'ability_id': '123'}))[0]
        assert ability.name == payload['name']
        assert ability.tactic == payload['tactic']
        assert ability.ability_id == test_ability.ability_id
        assert ability.description == test_ability.description
        assert ability.technique_id == test_ability.technique_id
        assert ability.technique_name == test_ability.technique_name

    async def test_unauthorized_update_ability(self, api_client, test_ability):
        payload = dict(name='an updated test ability', tactic='defense-evasion')
        resp = await api_client.patch('/api/v2/abilities/123', json=payload)
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_update_nonexistent_ability(self, api_client, api_cookies):
        payload = dict(name='an updated test ability', tactic='defense-evasion')
        resp = await api_client.patch('/api/v2/abilities/999', cookies=api_cookies, json=payload)
        assert resp.status == HTTPStatus.NOT_FOUND

    async def test_replace_ability(self, api_client, api_cookies, test_ability):
        test_executor_linux = Executor(name='sh', platform='linux', command='whoami')
        payload = dict(name='replaced test ability', tactic='collection', technique_name='discovery', technique_id='2',
                       executors=[ExecutorSchema().dump(test_executor_linux)])
        resp = await api_client.put('/api/v2/abilities/123', cookies=api_cookies, json=payload)
        assert resp.status == HTTPStatus.OK
        ability = await resp.json()
        assert ability['name'] == payload['name']
        assert ability['technique_name'] == payload['technique_name']
        assert ability['technique_id'] == payload['technique_id']
        assert ability['tactic'] == payload['tactic']
        assert ability['ability_id'] == test_ability.ability_id

    async def test_unauthorized_replace_ability(self, api_client, test_ability):
        test_executor_linux = Executor(name='sh', platform='linux', command='whoami')
        payload = dict(name='replaced test ability', tactic='collection', technique_name='discovery', technique_id='2',
                       executors=[ExecutorSchema().dump(test_executor_linux)])
        resp = await api_client.put('/api/v2/abilities/123', json=payload)
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_replace_nonexistent_ability(self, api_client, api_cookies):
        test_executor_linux = Executor(name='sh', platform='linux', command='whoami')
        payload = dict(name='replaced test ability', tactic='collection', technique_name='discovery', technique_id='2',
                       executors=[ExecutorSchema().dump(test_executor_linux)])
        resp = await api_client.put('/api/v2/abilities/123', cookies=api_cookies, json=payload)
        assert resp.status == HTTPStatus.OK
        ability = await resp.json()
        assert ability['name'] == payload['name']
        assert ability['technique_name'] == payload['technique_name']
        assert ability['technique_id'] == payload['technique_id']
        assert ability['tactic'] == payload['tactic']
        assert ability['ability_id'] == '123'

    async def test_invalid_replace_ability(self, api_client, api_cookies, test_ability):
        payload = dict(name='replaced test ability', tactic='collection', technique_name='discovery', technique_id='2',
                       executors=[])
        resp = await api_client.put('/api/v2/abilities/123', cookies=api_cookies, json=payload)
        assert resp.status == HTTPStatus.BAD_REQUEST
