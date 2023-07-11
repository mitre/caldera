import pytest
import unittest.mock as mock

from http import HTTPStatus

from app.objects.c_source import Source, SourceSchema
from app.objects.secondclass.c_fact import Fact
from app.objects.secondclass.c_rule import Rule
from app.objects.secondclass.c_relationship import Relationship
from app.utility.rule_set import RuleAction
from app.utility.base_service import BaseService


@pytest.fixture
def new_source_payload():
    fact = {
        'trait': 'test_fact',
        'value': 1
    }
    rule = Rule(action=RuleAction.ALLOW, trait="test_rule")
    relationship = {
        'source': fact,
        'edge': 'alpha',
        'origin': "new_test_operation"
    }
    source = {
        'id': '456',
        'name': 'new test source',
        'facts': [fact],
        'rules': [rule.schema.dump(rule)],
        'relationships': [relationship],
        'plugin': ''
    }
    return source


@pytest.fixture
def expected_new_source_dump(new_source_payload, mocker, mock_time):
    with mocker.patch('app.objects.secondclass.c_fact.datetime') as mock_datetime:
        mock_datetime.return_value = mock_datetime
        mock_datetime.now.return_value = mock_time
        source = SourceSchema().load(new_source_payload)
        dumped_obj = source.display_schema.dump(source)
        dumped_obj['relationships'][0]['unique'] = mock.ANY
        return dumped_obj


@pytest.fixture
def updated_source_payload():
    fact = {
        'trait': 'updated_test_fact',
        'value': 2
    }
    rule = Rule(action=RuleAction.DENY, trait='updated_test_rule')
    relationship = {
        'source': fact,
        'edge': 'beta',
        'origin': "updated_test_operation"
    }
    source = {
        'id': '123',
        'name': 'updated test source',
        'facts': [fact],
        'rules': [rule.schema.dump(rule)],
        'relationships': [relationship]
    }
    return source


@pytest.fixture
def expected_updated_source_dump(updated_source_payload, mocker, mock_time):
    with mocker.patch('app.objects.secondclass.c_fact.datetime') as mock_datetime:
        mock_datetime.return_value = mock_datetime
        mock_datetime.now.return_value = mock_time
        source = SourceSchema().load(updated_source_payload)
        dumped_obj = source.display_schema.dump(source)
        dumped_obj['relationships'][0]['unique'] = mock.ANY
        dumped_obj['plugin'] = ''
        return dumped_obj


@pytest.fixture
def replaced_source_payload(test_source):
    source_data = test_source.schema.dump(test_source)
    fact = {
        'trait': 'replaced_test_fact',
        'value': 3
    }
    rule = Rule(action=RuleAction.DENY, trait='replaced_test_rule')
    relationship = {
        'source': fact,
        'edge': 'delta',
        'origin': "replaced_test_operation"
    }
    source_data.update(dict(name='a replaced test source',
                            facts=[fact],
                            rules=[rule.schema.dump(rule)],
                            relationships=[relationship]
                            ))
    return source_data


@pytest.fixture
def expected_replaced_source_dump(replaced_source_payload, mocker, mock_time):
    with mocker.patch('app.objects.secondclass.c_fact.datetime') as mock_datetime:
        mock_datetime.return_value = mock_datetime
        mock_datetime.now.return_value = mock_time
        source = SourceSchema().load(replaced_source_payload)
        dumped_obj = source.display_schema.dump(source)
        dumped_obj['relationships'][0]['unique'] = mock.ANY
        return dumped_obj


@pytest.fixture
def test_source(event_loop, mocker, mock_time):
    with mocker.patch('app.objects.secondclass.c_fact.datetime') as mock_datetime:
        mock_datetime.return_value = mock_datetime
        mock_datetime.now.return_value = mock_time
        fact = Fact(trait='test_fact', value=1)
        rule = Rule(RuleAction.ALLOW, trait='test_rule')
        relationship = Relationship(source=fact, edge="alpha", origin="test_operation")
        source = Source(id='123', name='Test Source', facts=[fact],
                        rules=[rule], adjustments=[], relationships=[relationship])
        event_loop.run_until_complete(BaseService.get_service('data_svc').store(source))
        return source


class TestSourcesApi:
    async def test_get_sources(self, api_v2_client, api_cookies, test_source):
        resp = await api_v2_client.get('/api/v2/sources', cookies=api_cookies)
        sources_list = await resp.json()
        assert len(sources_list) == 1
        source_dict = sources_list[0]
        assert source_dict == test_source.display_schema.dump(test_source)

    async def test_unauthorized_get_sources(self, api_v2_client, test_source):
        resp = await api_v2_client.get('/api/v2/sources')
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_get_source_by_id(self, api_v2_client, api_cookies, test_source):
        resp = await api_v2_client.get('/api/v2/sources/123', cookies=api_cookies)
        source_dict = await resp.json()
        assert source_dict == test_source.display_schema.dump(test_source)

    async def test_unauthorized_get_source_by_id(self, api_v2_client, test_source):
        resp = await api_v2_client.get('/api/v2/sources/123')
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_get_nonexistent_source_by_id(self, api_v2_client, api_cookies):
        resp = await api_v2_client.get('/api/v2/sources/999', cookies=api_cookies)
        assert resp.status == HTTPStatus.NOT_FOUND

    async def test_create_source(self, api_v2_client, api_cookies, new_source_payload, expected_new_source_dump,
                                 mocker, mock_time):
        with mocker.patch('app.objects.secondclass.c_fact.datetime') as mock_datetime:
            mock_datetime.return_value = mock_datetime
            mock_datetime.now.return_value = mock_time
            resp = await api_v2_client.post('/api/v2/sources', cookies=api_cookies, json=new_source_payload)
            assert resp.status == HTTPStatus.OK
            source_data = await resp.json()
            assert source_data == expected_new_source_dump
            stored_source = (await BaseService.get_service('data_svc').locate('sources', {'id': '456'}))[0]
            assert stored_source.display_schema.dump(stored_source) == expected_new_source_dump

    async def test_unauthorized_create_source(self, api_v2_client, new_source_payload):
        resp = await api_v2_client.post('/api/v2/sources', json=new_source_payload)
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_create_duplicate_source(self, api_v2_client, api_cookies, test_source):
        payload = test_source.schema.dump(test_source)
        resp = await api_v2_client.post('/api/v2/sources', cookies=api_cookies, json=payload)
        assert resp.status == HTTPStatus.BAD_REQUEST

    async def test_update_source(self, api_v2_client, api_cookies, test_source, updated_source_payload,
                                 expected_updated_source_dump, mocker, mock_time):
        with mocker.patch('app.api.v2.managers.base_api_manager.BaseApiManager.strip_yml') as mock_strip_yml:
            mock_strip_yml.return_value = [test_source.schema.dump(test_source)]
            with mocker.patch('app.objects.secondclass.c_fact.datetime') as mock_datetime:
                mock_datetime.return_value = mock_datetime
                mock_datetime.now.return_value = mock_time
                resp = await api_v2_client.patch('/api/v2/sources/123', cookies=api_cookies, json=updated_source_payload)
                assert resp.status == HTTPStatus.OK
                source_data = await resp.json()
                assert source_data == expected_updated_source_dump
                source = (await BaseService.get_service('data_svc').locate('sources', {'id': '123'}))[0]
                assert source.display_schema.dump(source) == expected_updated_source_dump

    async def test_unauthorized_update_source(self, api_v2_client, test_source, updated_source_payload):
        resp = await api_v2_client.patch('/api/v2/sources/123', json=updated_source_payload)
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_update_nonexistent_source(self, api_v2_client, api_cookies, updated_source_payload):
        resp = await api_v2_client.patch('/api/v2/sources/999', cookies=api_cookies, json=updated_source_payload)
        assert resp.status == HTTPStatus.NOT_FOUND

    async def test_replace_source(self, api_v2_client, api_cookies, test_source, replaced_source_payload, mocker,
                                  mock_time, expected_replaced_source_dump):
        with mocker.patch('app.objects.secondclass.c_fact.datetime') as mock_datetime:
            mock_datetime.return_value = mock_datetime
            mock_datetime.now.return_value = mock_time
            resp = await api_v2_client.put('/api/v2/sources/123', cookies=api_cookies, json=replaced_source_payload)
            assert resp.status == HTTPStatus.OK
            source = await resp.json()
            assert source == expected_replaced_source_dump
            source = (await BaseService.get_service('data_svc').locate('sources', {'id': '123'}))[0]
            assert source.display_schema.dump(source) == expected_replaced_source_dump

    async def test_unauthorized_replace_source(self, api_v2_client, test_source, replaced_source_payload):
        resp = await api_v2_client.put('/api/v2/sources/123', json=replaced_source_payload)
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_replace_nonexistent_source(self, api_v2_client, api_cookies, new_source_payload, mocker, mock_time,
                                              expected_new_source_dump):
        with mocker.patch('app.objects.secondclass.c_fact.datetime') as mock_datetime:
            mock_datetime.return_value = mock_datetime
            mock_datetime.now.return_value = mock_time
            resp = await api_v2_client.put('/api/v2/sources/456', cookies=api_cookies, json=new_source_payload)
            assert resp.status == HTTPStatus.OK
            source = await resp.json()
            assert source == expected_new_source_dump
            source = (await BaseService.get_service('data_svc').locate('sources', {'id': '456'}))[0]
            assert source.display_schema.dump(source) == expected_new_source_dump
