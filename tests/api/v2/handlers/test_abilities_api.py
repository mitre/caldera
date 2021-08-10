import pytest

from http import HTTPStatus

from app.objects.c_ability import Ability
from app.objects.secondclass.c_executor import Executor, ExecutorSchema
from app.utility.base_service import BaseService


@pytest.fixture
def setup_abilities_api_test(loop, api_client, executor):
    test_executor_linux = executor(name='sh', platform='linux')
    test_ability = Ability(ability_id='123', name='Test Ability', executors=[test_executor_linux])
    loop.run_until_complete(BaseService.get_service('data_svc').store(test_ability))


@pytest.mark.usefixtures(
    "setup_abilities_api_test"
)
class TestAbilitiesApi:
    async def test_get_abilities(self, api_client, api_cookies):
        resp = await api_client.get('/api/v2/abilities', cookies=api_cookies)
        abilities_list = await resp.json()
        assert len(abilities_list) == 1
        ability_dict = abilities_list[0]
        assert ability_dict['ability_id'] == '123'
        assert ability_dict['name'] == 'Test Ability'

    async def test_get_ability_by_id(self, api_client, api_cookies):
        resp = await api_client.get('/api/v2/abilities/123', cookies=api_cookies)
        ability_dict = await resp.json()
        assert ability_dict['ability_id'] == '123'
        assert ability_dict['name'] == 'Test Ability'

    async def test_unauthorized_get_ability_by_id(self, api_client):
        resp = await api_client.get('/api/v2/abilities/123')
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_delete_ability_by_id(self, api_client, api_cookies):
        ability_exists = await BaseService.get_service('data_svc').locate('abilities', {'ability_id': '123'})
        assert ability_exists
        resp = await api_client.delete('/api/v2/abilities/123', cookies=api_cookies)
        assert resp.status == HTTPStatus.NO_CONTENT
        ability_exists = await BaseService.get_service('data_svc').locate('abilities', {'ability_id': '123'})
        assert not ability_exists

    async def test_create_ability(self, api_client, api_cookies, mocker, async_return):
        test_executor_linux = Executor(name='sh', platform='linux', command='whoami')
        payload = dict(name='new test ability', ability_id='456', tactic='collection', technique_name='collection',
                       technique_id='1', executors=[ExecutorSchema().dump(test_executor_linux)])
        resp = await api_client.post('/api/v2/abilities', cookies=api_cookies, json=payload)
        assert resp.status == HTTPStatus.OK
        ability_data = await resp.json()
        assert ability_data.get('name') == "new test ability"
        ability_exists = await BaseService.get_service('data_svc').locate('abilities', {'ability_id': '456'})
        assert ability_exists

    async def test_update_ability(self, api_client, api_cookies):
        payload = dict(name='an updated test ability', tactic='defense-evasion')
        resp = await api_client.patch('/api/v2/abilities/123', cookies=api_cookies, json=payload)
        assert resp.status == HTTPStatus.OK
        ability = (await BaseService.get_service('data_svc').locate('abilities', {'ability_id': '123'}))[0]
        assert ability.name == payload['name']
        assert ability.tactic == payload['tactic']

    async def test_replace_ability(self, api_client, api_cookies):
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
