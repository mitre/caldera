from http import HTTPStatus

# noinspection PyUnresolvedReferences
from tests.web_server.fixtures import *  # noqa F403, F401


async def test_read_agent(aiohttp_client, authorized_cookies, sample_agent):
    resp = await aiohttp_client.post('/api/rest', json=dict(index='agents'), cookies=authorized_cookies)
    assert resp.status == HTTPStatus.OK
    agent_list = await resp.json()
    assert len(list(filter(lambda x: x['paw'] == sample_agent.paw, agent_list)))


async def test_modify_agent(aiohttp_client, authorized_cookies, sample_agent):
    resp = await aiohttp_client.put('/api/rest', json=dict(index='agents', paw=sample_agent.paw,
                                                           sleep_min=1, sleep_max=5), cookies=authorized_cookies)
    assert resp.status == HTTPStatus.OK
    agent_dict = await resp.json()
    assert agent_dict['sleep_max'] == 5
    assert sample_agent.sleep_min == 1
    assert sample_agent.sleep_max == 5
