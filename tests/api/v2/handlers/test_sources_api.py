import pytest

from http import HTTPStatus
from datetime import datetime, timezone

from app.objects.c_source import Source
from app.objects.secondclass.c_fact import Fact
from app.objects.secondclass.c_rule import Rule
from app.objects.secondclass.c_relationship import Relationship
from app.utility.rule_set import RuleAction
from app.utility.base_service import BaseService


@pytest.fixture
def mock_time():
    return datetime(2021, 1, 1, tzinfo=timezone.utc)


@pytest.fixture
def new_source_payload(mocker, mock_time):
    with mocker.patch('datetime.datetime') as mock_datetime:
        mock_datetime.return_value = mock_datetime
        mock_datetime.now.return_value = mock_time
        fact = Fact(trait='test_fact', value=1)
        rule = Rule(RuleAction.ALLOW, trait='test_rule')
        relationship = Relationship(source=fact, edge="alpha", origin="new_test_operation")
        source = {
            'id': '456',
            'name': 'new test source',
            'facts': [fact.schema.dump(fact)],
            'rules': [rule.schema.dump(rule)],
            'relationships': [relationship.schema.dump(relationship)]
        }
        return source


@pytest.fixture
def updated_source_payload(test_source, mocker, mock_time):
    with mocker.patch('datetime.datetime') as mock_datetime:
        mock_datetime.return_value = mock_datetime
        mock_datetime.now.return_value = mock_time
        source_data = test_source.schema.dump(test_source)
        new_fact = Fact(trait='new_test_fact', value=2)
        new_rule = Rule(RuleAction.DENY, trait='new_test_rule')
        new_relationship = Relationship(source=new_fact, edge="beta", origin="test_operation_2")
        source_data.update(dict(name='an updated test source',
                                facts=[new_fact.schema.dump(new_fact)],
                                rules=[new_rule.schema.dump(new_rule)],
                                relationships=[new_relationship.schema.dump(new_relationship)]
                                ))
        return source_data


@pytest.fixture
def replaced_source_payload(test_source, mocker, mock_time):
    with mocker.patch('datetime.datetime') as mock_datetime:
        mock_datetime.return_value = mock_datetime
        mock_datetime.now.return_value = mock_time
        source_data = test_source.schema.dump(test_source)
        new_fact = Fact(trait='replaced_test_fact', value=2)
        new_rule = Rule(RuleAction.ALLOW, trait='replaced_test_rule')
        new_relationship = Relationship(source=new_fact, edge="alpha", origin="test_operation_3")
        source_data.update(dict(name='an replaced test source',
                                facts=[new_fact.schema.dump(new_fact)],
                                rules=[new_rule.schema.dump(new_rule)],
                                relationships=[new_relationship.schema.dump(new_relationship)]
                                ))
        return source_data


@pytest.fixture
def test_source(loop, api_v2_client, executor, mocker, mock_time):
    with mocker.patch('datetime.datetime') as mock_datetime:
        mock_datetime.return_value = mock_datetime
        mock_datetime.now.return_value = mock_time
        fact = Fact(trait='test_fact', value=1)
        rule = Rule(RuleAction.ALLOW, trait='test_rule')
        relationship = Relationship(source=fact, edge="alpha", origin="test_operation")
        source = Source(id='123', name='Test Source', facts=[fact],
                        rules=[rule], adjustments=[], relationships=[relationship])
        loop.run_until_complete(BaseService.get_service('data_svc').store(source))
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

    async def test_create_source(self, api_v2_client, api_cookies, new_source_payload):
        resp = await api_v2_client.post('/api/v2/sources', cookies=api_cookies, json=new_source_payload)
        assert resp.status == HTTPStatus.OK
        source_data = await resp.json()
        assert source_data == new_source_payload
        source_exists = await BaseService.get_service('data_svc').locate('sources', {'source_id': '456'})
        assert source_exists

    async def test_unauthorized_create_source(self, api_v2_client, new_source_payload):
        resp = await api_v2_client.post('/api/v2/sources', json=new_source_payload)
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_create_duplicate_source(self, api_v2_client, api_cookies, mocker, async_return, test_source):
        payload = test_source.schema.dump(test_source)
        resp = await api_v2_client.post('/api/v2/sources', cookies=api_cookies, json=payload)
        assert resp.status == HTTPStatus.BAD_REQUEST

    async def test_update_source(self, api_v2_client, api_cookies, test_source, updated_source_payload):
        resp = await api_v2_client.patch('/api/v2/sources/123', cookies=api_cookies, json=updated_source_payload)
        assert resp.status == HTTPStatus.OK
        source = (await BaseService.get_service('data_svc').locate('sources', {'source_id': '123'}))[0]
        assert source.schema.dump(source) == updated_source_payload

    async def test_unauthorized_update_source(self, api_v2_client, test_source, updated_source_payload):
        resp = await api_v2_client.patch('/api/v2/sources/123', json=updated_source_payload)
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_update_nonexistent_source(self, api_v2_client, api_cookies, updated_source_payload):
        resp = await api_v2_client.patch('/api/v2/sources/999', cookies=api_cookies, json=updated_source_payload)
        assert resp.status == HTTPStatus.NOT_FOUND

    async def test_replace_source(self, api_v2_client, api_cookies, test_source, replaced_source_payload):
        resp = await api_v2_client.put('/api/v2/sources/123', cookies=api_cookies, json=replaced_source_payload)
        assert resp.status == HTTPStatus.OK
        source = await resp.json()
        assert source == replaced_source_payload

    async def test_unauthorized_replace_source(self, api_v2_client, test_source, replaced_source_payload):
        resp = await api_v2_client.put('/api/v2/sources/123', json=replaced_source_payload)
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_replace_nonexistent_source(self, api_v2_client, api_cookies, new_source_payload):
        resp = await api_v2_client.put('/api/v2/sources/456', cookies=api_cookies, json=new_source_payload)
        assert resp.status == HTTPStatus.OK
        source = await resp.json()
        assert source == new_source_payload

    async def test_invalid_replace_source(self, api_v2_client, api_cookies, test_source):
        payload = dict(name='replaced test source', tactic='collection', technique_name='discovery', technique_id='2',
                       executors=[])
        resp = await api_v2_client.put('/api/v2/sources/123', cookies=api_cookies, json=payload)
        assert resp.status == HTTPStatus.BAD_REQUEST
