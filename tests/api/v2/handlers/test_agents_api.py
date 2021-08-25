from http import HTTPStatus

import pytest

from app.objects.c_agent import Agent
from app.utility.base_service import BaseService


@pytest.fixture
def updated_agent_payload():
    return {
        'group': 'blue',
        'trusted': False,
        'sleep_min': 1,
        'sleep_max': 5,
        'watchdog': 0,
        'pending_contact': 'HTML'
    }


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
        'origin_link_id': 0,
        'deadman_enabled': True,
        'available_contacts': [],
        'host_ip_addrs': []
    }


@pytest.fixture
def test_agent(loop):
    test_agent = Agent(paw='123', sleep_min=2, sleep_max=8, watchdog=0, executors=['sh'], platform='linux')
    loop.run_until_complete(BaseService.get_service('data_svc').store(test_agent))
    return test_agent


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

    async def test_create_agent(self, api_v2_client, api_cookies, new_agent_payload):
        resp = await api_v2_client.post('/api/v2/agents', cookies=api_cookies, json=new_agent_payload)
        assert resp.status == HTTPStatus.OK
        agent_dict = await resp.json()
        assert agent_dict['sleep_min'] == new_agent_payload['sleep_min']
        assert agent_dict['sleep_max'] == new_agent_payload['sleep_max']
        assert agent_dict['paw'] == new_agent_payload['paw']
        assert agent_dict['executors'] == new_agent_payload['executors']

    async def test_unauthorized_create_agent(self, api_v2_client, new_agent_payload):
        resp = await api_v2_client.post('/api/v2/agents', json=new_agent_payload)
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_update_agent(self, api_v2_client, api_cookies, test_agent, updated_agent_payload):
        resp = await api_v2_client.patch('/api/v2/agents/123', cookies=api_cookies, json=updated_agent_payload)
        assert resp.status == HTTPStatus.OK
        agent_dict = await resp.json()
        assert agent_dict['sleep_min'] == updated_agent_payload['sleep_min']
        assert agent_dict['sleep_max'] == updated_agent_payload['sleep_max']
        assert agent_dict['group'] == updated_agent_payload['group']
        assert agent_dict['trusted'] == updated_agent_payload['trusted']
        assert agent_dict['pending_contact'] == updated_agent_payload['pending_contact']

    async def test_unauthorized_update_agent(self, api_v2_client, test_agent, updated_agent_payload):
        resp = await api_v2_client.patch('/api/v2/agents/123', json=updated_agent_payload)
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_nonexistent_update_agent(self, api_v2_client, api_cookies, updated_agent_payload):
        resp = await api_v2_client.patch('/api/v2/agents/999', cookies=api_cookies, json=updated_agent_payload)
        assert resp.status == HTTPStatus.NOT_FOUND

    async def test_create_or_update_agent(self, api_v2_client, api_cookies, test_agent, updated_agent_payload):
        resp = await api_v2_client.put('/api/v2/agents/123', cookies=api_cookies, json=updated_agent_payload)
        assert resp.status == HTTPStatus.OK
        agent_dict = await resp.json()
        assert agent_dict['sleep_min'] == updated_agent_payload['sleep_min']
        assert agent_dict['sleep_max'] == updated_agent_payload['sleep_max']
        assert agent_dict['group'] == updated_agent_payload['group']
        assert agent_dict['trusted'] == updated_agent_payload['trusted']
        assert agent_dict['pending_contact'] == updated_agent_payload['pending_contact']

    async def test_unauthorized_create_or_update_agent(self, api_v2_client, test_agent, updated_agent_payload):
        resp = await api_v2_client.put('/api/v2/agents/123', json=updated_agent_payload)
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_nonexistent_create_or_update_agent(self, api_v2_client, api_cookies, new_agent_payload):
        resp = await api_v2_client.put('/api/v2/agents/456', cookies=api_cookies, json=new_agent_payload)
        assert resp.status == HTTPStatus.OK
        agent_dict = await resp.json()
        assert agent_dict['sleep_min'] == new_agent_payload['sleep_min']
        assert agent_dict['sleep_max'] == new_agent_payload['sleep_max']
        assert agent_dict['paw'] == new_agent_payload['paw']
        assert agent_dict['executors'] == new_agent_payload['executors']
    '''
    async def test_delete_agent(self, api_v2_client, api_cookies, test_agent):
        pass

    async def test_get_deploy_commands(self, api_v2_client, api_cookies, test_agent):
        pass

    async def test_unauthorized_get_deploy_commands(self, api_v2_client, test_agent):
        resp = await api_v2_client.patch('/api/v2/deploy_commands/}', json=)
        assert resp.status == HTTPStatus.FORBIDDEN
    '''
