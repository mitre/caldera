from http import HTTPStatus

import pytest

from app.objects.c_ability import AbilitySchema
from app.objects.c_agent import Agent
from app.objects.secondclass.c_executor import ExecutorSchema
from app.utility.base_service import BaseService


@pytest.fixture
def updated_agent_fields_payload():
    return {
        'group': 'blue',
        'trusted': False,
        'sleep_min': 1,
        'sleep_max': 5,
        'watchdog': 0,
        'pending_contact': 'HTML'
    }


@pytest.fixture
def expected_updated_agent_dump(test_agent, updated_agent_fields_payload):
    expected_payload = test_agent.schema.dump(test_agent)
    expected_payload.update(updated_agent_fields_payload)
    return expected_payload


@pytest.fixture
def new_agent_payload():
    return {
        'paw': '456',
        'sleep_min': 3,
        'sleep_max': 6,
        'watchdog': 0,
        'group': 'red',
        'architecture': '',
        'platform': 'linux',
        'server': 'http://localhost:8000',
        'upstream_dest': 'http://localhost:8000',
        'username': 'test',
        'location': './splunkd',
        'pid': 1,
        'ppid': 1,
        'trusted': True,
        'executors': ['sh'],
        'privilege': 'User',
        'exe_name': 'splunkd',
        'host': 'test_agent',
        'contact': 'HTTP',
        'proxy_receivers': {},
        'proxy_chain': [],
        'origin_link_id': '',
        'deadman_enabled': True,
        'available_contacts': ['HTTP'],
        'host_ip_addrs': []
    }


@pytest.fixture
def expected_new_agent_dump(new_agent_payload, mocker, mock_time):
    with mocker.patch('app.objects.c_agent.datetime') as mock_datetime:
        mock_datetime.return_value = mock_datetime
        mock_datetime.now.return_value = mock_time
        agent = Agent().load(new_agent_payload)
        return agent.schema.dump(agent)


@pytest.fixture
def test_agent(event_loop, mocker, mock_time):
    with mocker.patch('app.objects.c_agent.datetime') as mock_datetime:
        mock_datetime.return_value = mock_datetime
        mock_datetime.now.return_value = mock_time
        test_agent = Agent(paw='123', sleep_min=2, sleep_max=8, watchdog=0, executors=['sh'], platform='linux')
        event_loop.run_until_complete(BaseService.get_service('data_svc').store(test_agent))
        return test_agent


@pytest.fixture
def test_executor(test_agent):
    return ExecutorSchema().load(dict(timeout=60, platform=test_agent.platform, name='linux',
                                      command='ls'))


@pytest.fixture
def deploy_ability(test_executor, event_loop):
    ability = AbilitySchema().load(dict(ability_id='123',
                                        tactic='persistence',
                                        technique_id='auto-generated',
                                        technique_name='auto-generated',
                                        name='test deploy command',
                                        description='test ability',
                                        executors=[ExecutorSchema().dump(test_executor)]))
    event_loop.run_until_complete(BaseService.get_service('data_svc').store(ability))
    return ability


@pytest.fixture
def raw_ability(deploy_ability, test_executor):
    raw_ability = {
        'name': deploy_ability.name,
        'platform': test_executor.platform,
        'executor': test_executor.name,
        'description': deploy_ability.description,
        'command': test_executor.command,
        'variations': [{'description': v.description, 'command': v.raw_command} for v in test_executor.variations]
    }
    return raw_ability


@pytest.fixture
def combined_config(agent_config, app_config):
    main_config = app_config.copy()
    for key in main_config:
        if key.startswith('app'):
            continue
        app_config.pop(key)
    app_config.update({f'agents.{k}': v for k, v in agent_config.items()})
    return app_config


class TestAgentsApi:
    async def test_get_agents(self, api_v2_client, api_cookies, test_agent):
        resp = await api_v2_client.get('/api/v2/agents', cookies=api_cookies)
        assert resp.status == HTTPStatus.OK
        agents_list = await resp.json()
        assert len(agents_list) == 1
        agents_dict = agents_list[0]
        assert agents_dict == test_agent.schema.dump(test_agent)

    async def test_unauthorized_get_agents(self, api_v2_client, test_agent):
        resp = await api_v2_client.get('/api/v2/agents')
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_get_agent_by_id(self, api_v2_client, api_cookies, test_agent):
        resp = await api_v2_client.get('/api/v2/agents/123', cookies=api_cookies)
        assert resp.status == HTTPStatus.OK
        agent_dict = await resp.json()
        assert agent_dict == test_agent.schema.dump(test_agent)

    async def test_unauthorized_get_agent_by_id(self, api_v2_client, test_agent):
        resp = await api_v2_client.get('/api/v2/agents/123')
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_nonexistent_get_agent_by_id(self, api_v2_client, api_cookies):
        resp = await api_v2_client.get('/api/v2/agents/999', cookies=api_cookies)
        assert resp.status == HTTPStatus.NOT_FOUND

    async def test_create_agent(self, api_v2_client, api_cookies, new_agent_payload, mocker, expected_new_agent_dump,
                                mock_time):
        with mocker.patch('app.objects.c_agent.datetime') as mock_datetime:
            mock_datetime.return_value = mock_datetime
            mock_datetime.now.return_value = mock_time
            resp = await api_v2_client.post('/api/v2/agents', cookies=api_cookies, json=new_agent_payload)
            assert resp.status == HTTPStatus.OK
            agent_dict = await resp.json()
            assert agent_dict == expected_new_agent_dump
            stored_agent = (await BaseService.get_service('data_svc').locate('agents', {'paw': agent_dict['paw']}))[0]
            assert stored_agent.schema.dump(stored_agent) == expected_new_agent_dump

    async def test_unauthorized_create_agent(self, api_v2_client, new_agent_payload):
        resp = await api_v2_client.post('/api/v2/agents', json=new_agent_payload)
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_update_agent(self, api_v2_client, api_cookies, test_agent, updated_agent_fields_payload,
                                expected_updated_agent_dump):
        resp = await api_v2_client.patch('/api/v2/agents/123', cookies=api_cookies, json=updated_agent_fields_payload)
        assert resp.status == HTTPStatus.OK
        agent_dict = await resp.json()
        assert agent_dict == expected_updated_agent_dump
        stored_agent = (await BaseService.get_service('data_svc').locate('agents', {'paw': agent_dict['paw']}))[0]
        assert stored_agent.schema.dump(stored_agent) == expected_updated_agent_dump

    async def test_unauthorized_update_agent(self, api_v2_client, test_agent, updated_agent_fields_payload):
        resp = await api_v2_client.patch('/api/v2/agents/123', json=updated_agent_fields_payload)
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_nonexistent_update_agent(self, api_v2_client, api_cookies, updated_agent_fields_payload):
        resp = await api_v2_client.patch('/api/v2/agents/999', cookies=api_cookies, json=updated_agent_fields_payload)
        assert resp.status == HTTPStatus.NOT_FOUND

    async def test_create_or_update_existing_agent(self, api_v2_client, api_cookies, test_agent, mocker,
                                                   updated_agent_fields_payload, expected_updated_agent_dump):
        resp = await api_v2_client.put('/api/v2/agents/123', cookies=api_cookies, json=updated_agent_fields_payload)
        assert resp.status == HTTPStatus.OK
        agent_dict = await resp.json()
        assert agent_dict == expected_updated_agent_dump
        stored_agent = (await BaseService.get_service('data_svc').locate('agents', {'paw': agent_dict['paw']}))[0]
        assert stored_agent.schema.dump(stored_agent) == expected_updated_agent_dump

    async def test_unauthorized_create_or_update_agent(self, api_v2_client, test_agent, updated_agent_fields_payload):
        resp = await api_v2_client.put('/api/v2/agents/123', json=updated_agent_fields_payload)
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_create_or_update_nonexistent_agent(self, api_v2_client, api_cookies, new_agent_payload,
                                                      expected_new_agent_dump, mocker, mock_time):
        with mocker.patch('app.objects.c_agent.datetime') as mock_datetime:
            mock_datetime.return_value = mock_datetime
            mock_datetime.now.return_value = mock_time
            resp = await api_v2_client.put('/api/v2/agents/456', cookies=api_cookies, json=new_agent_payload)
            assert resp.status == HTTPStatus.OK
            agent_dict = await resp.json()
            assert agent_dict == expected_new_agent_dump
            stored_agent = (await BaseService.get_service('data_svc').locate('agents', {'paw': agent_dict['paw']}))[0]
            assert stored_agent.schema.dump(stored_agent) == expected_new_agent_dump

    async def test_get_deploy_commands(self, api_v2_client, api_cookies, deploy_ability, mocker, raw_ability,
                                       agent_config, app_config, combined_config):
        with mocker.patch('app.api.v2.managers.agent_api_manager.AgentApiManager.get_config') as mock_config:
            mock_config.side_effect = [[deploy_ability.ability_id], app_config, agent_config]
            resp = await api_v2_client.get('/api/v2/deploy_commands', cookies=api_cookies)
            assert resp.status == HTTPStatus.OK
            result = await resp.json()
            assert result['app_config'] == combined_config
            assert result['abilities'] == [raw_ability]

    async def test_unauthorized_get_deploy_commands(self, api_v2_client, deploy_ability):
        resp = await api_v2_client.get('/api/v2/deploy_commands')
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_get_deploy_commands_for_ability(self, api_v2_client, api_cookies, deploy_ability, mocker,
                                                   raw_ability, agent_config, app_config, combined_config):
        with mocker.patch('app.api.v2.managers.agent_api_manager.AgentApiManager.get_config') as mock_config:
            mock_config.side_effect = [app_config, agent_config]
            resp = await api_v2_client.get(f'/api/v2/deploy_commands/{deploy_ability.ability_id}', cookies=api_cookies)
            assert resp.status == HTTPStatus.OK
            result = await resp.json()
            assert result['app_config'] == combined_config
            assert result['abilities'] == [raw_ability]

    async def test_unauthorized_get_deploy_commands_for_ability(self, api_v2_client, deploy_ability):
        resp = await api_v2_client.get(f'/api/v2/deploy_commands/{deploy_ability.ability_id}')
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_get_deploy_commands_for_nonexistent_ability(self, api_v2_client, api_cookies, mocker, agent_config,
                                                               app_config, combined_config):
        with mocker.patch('app.api.v2.managers.agent_api_manager.AgentApiManager.get_config') as mock_config:
            mock_config.side_effect = [app_config, agent_config]
            resp = await api_v2_client.get('/api/v2/deploy_commands/999', cookies=api_cookies)
            assert resp.status == HTTPStatus.OK
            result = await resp.json()
            assert result['app_config'] == combined_config
            assert result['abilities'] == []
