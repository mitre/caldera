import pytest
from http import HTTPStatus

from app.objects.c_operation import Operation
from app.objects.c_adversary import Adversary
from app.objects.c_agent import Agent
from app.objects.c_source import Source


@pytest.fixture
def setup_operations_api_test(loop, data_svc):
    expected_adversary = {'description': 'an empty adversary profile', 'name': 'ad-hoc',
                          'adversary_id': 'ad-hoc', 'atomic_ordering': [],
                          'objective': '495a9828-cab1-44dd-a0ca-66e58177d8cc',
                          'tags': [], 'has_repeatable_abilities': False}
    expected_operation = {'name': 'My Test Operation',
                          'adversary': expected_adversary,
                          'state': 'finished',
                          'planner': {'name': 'test', 'description': None, 'module': 'test',
                                      'stopping_conditions': [], 'params': {}, 'allow_repeatable_abilities': False,
                                      'ignore_enforcement_modules': [], 'id': '123'}, 'jitter': '2/8',
                          'host_group': [{'trusted': True, 'architecture': 'unknown', 'watchdog': 0,
                                          'contact': 'unknown', 'username': 'unknown', 'links': [], 'sleep_max': 8,
                                          'exe_name': 'unknown', 'executors': ['pwsh', 'psh'], 'ppid': 0,
                                          'sleep_min': 2, 'server': '://None:None', 'platform': 'windows',
                                          'host': 'unknown', 'paw': '123', 'pid': 0,
                                          'display_name': 'unknown$unknown', 'group': 'red', 'location': 'unknown',
                                          'privilege': 'User', 'proxy_receivers': {}, 'proxy_chain': [],
                                          'origin_link_id': 0, 'deadman_enabled': False,
                                          'available_contacts': ['unknown'], 'pending_contact': 'unknown',
                                          'host_ip_addrs': [], 'upstream_dest': '://None:None'}],
                          'visibility': 50, 'autonomous': 1, 'chain': [], 'auto_close': False,
                          'obfuscator': 'plain-text', 'use_learning_parsers': False,
                          'objective': {'goals': [{'value': 'complete',
                                                   'operator': '==',
                                                   'target': 'exhaustion',
                                                   'achieved': False,
                                                   'count': 1048576}],
                                        'percentage': 0.0, 'description': '',
                                        'id': '495a9828-cab1-44dd-a0ca-66e58177d8cc',
                                        'name': 'default'}}
    test_adversary = Adversary(name=expected_adversary['name'], adversary_id=expected_adversary['adversary_id'],
                               description=expected_adversary['description'], objective=expected_adversary['objective'],
                               tags=expected_adversary['tags'])
    loop.run_until_complete(data_svc.store(test_adversary))

    test_agent = Agent(paw='123', sleep_min=2, sleep_max=8, watchdog=0, executors=['pwsh', 'psh'], platform='windows')
    loop.run_until_complete(data_svc.store(test_agent))

    test_source = Source(id='123', name='test', facts=[], adjustments=[])
    loop.run_until_complete(data_svc.store(test_source))

    test_operation = Operation(name=expected_operation['name'], adversary=test_adversary, agents=[test_agent], id='123',
                               source=test_source, state=expected_operation['state'])
    loop.run_until_complete(data_svc.store(test_operation))


@pytest.mark.usefixtures(
    "setup_operations_api_test"
)
class TestOperationsApi:
    async def test_get_operations(self, api_client, authorized_cookies):
        resp = await api_client.get('/api/v2/operations', cookies=authorized_cookies)
        operations_list = await resp.json()
        assert len(operations_list) == 1
        operation_dict = operations_list[0]
        assert operation_dict['name'] == 'My Test Operation'
        assert operation_dict['id'] == '123'

    async def test_get_operation_by_id(self, api_client, authorized_cookies):
        resp = await api_client.get('/api/v2/operations/123', cookies=authorized_cookies)
        operation_dict = await resp.json()
        assert operation_dict['name'] == 'My Test Operation'
        assert operation_dict['id'] == '123'

    async def test_unauthorized_get_operation_by_id(self, api_client):
        resp = await api_client.get('/api/v2/operations')
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_delete_operation_by_id(self, data_svc, api_client, authorized_cookies):
        op_exists = await data_svc.locate('operations', {'id': '123'})
        assert op_exists
        resp = await api_client.delete('/api/v2/operations/123', cookies=authorized_cookies)
        assert resp.status == HTTPStatus.NO_CONTENT
        op_exists = await data_svc.locate('operations', {'id': '123'})
        assert not op_exists

    async def test_get_operation_report(self, data_svc, api_client, authorized_cookies):
        resp = await api_client.get('/api/v2/operations/123', cookies=authorized_cookies)
        report = await resp.json()
        assert report['name'] == 'My Test Operation'
        assert report['state'] == 'finished'
