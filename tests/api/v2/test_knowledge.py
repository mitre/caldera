import pytest
from aiohttp import web

from app.service.app_svc import AppService
from app.service.auth_svc import AuthService, CONFIG_API_KEY_RED
from app.service.file_svc import FileSvc
from app.service.data_svc import DataService
from app.service.event_svc import EventService
from app.service.contact_svc import ContactService
from app.utility.base_service import BaseService
from app.utility.base_world import BaseWorld
from app.api.v2.handlers.fact_api import FactApi
from app.api.v2.responses import json_request_validation_middleware
from app.api.v2.security import authentication_required_middleware_factory
from app.objects.secondclass.c_fact import WILDCARD_STRING
from app.service.knowledge_svc import KnowledgeService

cakr = 'abc123'
headers = {'key': cakr, 'Content-Type': 'application/json'}


@pytest.fixture
def base_world():

    BaseWorld.apply_config(
        name='main',
        config={
            CONFIG_API_KEY_RED: cakr,

            'users': {
                'red': {'reduser': 'redpass'},
                'blue': {'blueuser': 'bluepass'}
            },

            'crypt_salt': 'thisisdefinitelynotkosher',  # Salt for file service instantiation
            'encryption_key': 'andneitheristhis',  # fake encryption key for file service instantiation
        }
    )

    yield BaseWorld
    BaseWorld.clear_config()


@pytest.fixture
async def knowledge_webapp(event_loop, base_world, data_svc):
    app_svc = AppService(web.Application())
    app_svc.add_service('auth_svc', AuthService())
    app_svc.add_service('knowledge_svc', KnowledgeService())
    app_svc.add_service('data_svc', DataService())
    app_svc.add_service('event_svc', EventService())
    app_svc.add_service('contact_svc', ContactService())
    app_svc.add_service('file_svc', FileSvc())  # This needs to be done this way, or it we won't have a valid BaseWorld
    services = app_svc.get_services()
    app = web.Application(
        middlewares=[
            authentication_required_middleware_factory(services['auth_svc']),
            json_request_validation_middleware
        ]
    )
    FactApi(services).add_routes(app)
    await app_svc.register_contacts()
    return app


async def test_display_facts(knowledge_webapp, aiohttp_client, fire_event_mock):
    client = await aiohttp_client(knowledge_webapp)
    fact_data = {
        'trait': 'demo',
        'value': 'test'
    }
    await client.post('/facts', json=fact_data, headers=headers)
    resp = await client.get('/facts', json=fact_data, headers=headers)
    data = await resp.json()
    response = data['found']

    assert len(response) == 1
    assert response[0]['trait'] == 'demo'
    assert response[0]['value'] == 'test'
    assert response[0]['source'] == WILDCARD_STRING


async def test_display_operation_facts(knowledge_webapp, aiohttp_client, fire_event_mock):
    client = await aiohttp_client(knowledge_webapp)
    op_id_test = 'this_is_a_valid_operation_id'

    fact_data = {
        'trait': 'demo',
        'value': 'test',
        'source': op_id_test
    }
    await client.post('/facts', json=fact_data, headers=headers)
    resp = await client.get(f'/facts/{op_id_test}', headers=headers)
    data = await resp.json()
    response = data['found']

    assert len(response) == 1
    assert response[0]['trait'] == 'demo'
    assert response[0]['value'] == 'test'
    assert response[0]['source'] == op_id_test


async def test_display_relationships(knowledge_webapp, aiohttp_client, fire_event_mock):
    client = await aiohttp_client(knowledge_webapp)
    op_id_test = 'this_is_a_valid_operation_id'
    fact_data_a = {
        'trait': 'a',
        'value': '1',
    }
    fact_data_b = {
        'trait': 'b',
        'value': '2'
    }
    relationship_data = {
        'source': fact_data_a,
        'edge': 'gamma',
        'target': fact_data_b,
        'origin': op_id_test
    }
    await client.post('/relationships', json=relationship_data, headers=headers)
    resp = await client.get('/relationships', json=relationship_data, headers=headers)
    data = await resp.json()
    response = data['found']

    assert len(response) == 1
    assert response[0]['source']['trait'] == 'a'
    assert response[0]['source']['value'] == '1'
    assert response[0]['edge'] == 'gamma'
    assert response[0]['origin'] == 'this_is_a_valid_operation_id'
    assert response[0]['source']['source'] == 'this_is_a_valid_operation_id'


async def test_display_operation_relationships(knowledge_webapp, aiohttp_client, fire_event_mock):
    client = await aiohttp_client(knowledge_webapp)
    op_id_test = 'this_is_a_valid_operation_id'
    fact_data_a = {
        'trait': 'a',
        'value': '1',
        'source': op_id_test
    }
    fact_data_b = {
        'trait': 'b',
        'value': '2',
        'source': op_id_test
    }
    relationship_data = {
        'source': fact_data_a,
        'edge': 'gamma',
        'target': fact_data_b,
        'origin': op_id_test
    }
    await client.post('/relationships', json=relationship_data, headers=headers)
    resp = await client.get(f'/relationships/{op_id_test}', headers=headers)
    data = await resp.json()
    response = data['found']

    assert len(response) == 1
    assert response[0]['source']['trait'] == fact_data_a['trait']
    assert response[0]['source']['value'] == fact_data_a['value']
    assert response[0]['target']['trait'] == fact_data_b['trait']
    assert response[0]['target']['value'] == fact_data_b['value']
    assert response[0]['edge'] == relationship_data['edge']
    assert response[0]['origin'] == op_id_test
    assert response[0]['source']['source'] == op_id_test
    assert response[0]['target']['source'] == op_id_test


async def test_remove_fact(knowledge_webapp, aiohttp_client, fire_event_mock):
    client = await aiohttp_client(knowledge_webapp)
    fact_data = {
        'trait': 'demo',
        'value': 'test'
    }
    init = await client.post('/facts', json=fact_data, headers=headers)
    pre = await init.json()
    subs = await client.delete('/facts', json=fact_data, headers=headers)
    post = await subs.json()
    tmp = await client.get('/facts', json=fact_data, headers=headers)
    cur = await tmp.json()
    current = cur['found']
    start = pre['added']
    end = post['removed']
    assert len(start) == 1
    assert len(end) == 1
    assert len(current) == 0
    assert start == end


async def test_remove_relationship(knowledge_webapp, aiohttp_client, fire_event_mock):
    client = await aiohttp_client(knowledge_webapp)
    op_id_test = 'this_is_a_valid_operation_id'
    fact_data_a = {
        'trait': 'a',
        'value': '1',
    }
    fact_data_b = {
        'trait': 'b',
        'value': '2'
    }
    relationship_data = {
        'source': fact_data_a,
        'edge': 'alpha',
        'target': fact_data_b,
        'origin': op_id_test
    }
    init = await client.post('/relationships', json=relationship_data, headers=headers)
    pre = await init.json()
    subs = await client.delete('/relationships', json=dict(edge='alpha'), headers=headers)
    post = await subs.json()
    resp = await client.get('/relationships', json=relationship_data, headers=headers)
    cur = await resp.json()
    start = pre['added']
    end = post['removed']
    current = cur['found']
    assert len(start) == 1
    assert len(end) == 1
    assert len(current) == 0
    assert start == end


async def test_add_fact(knowledge_webapp, aiohttp_client, fire_event_mock):
    client = await aiohttp_client(knowledge_webapp)

    fact_data = {
        'trait': 'demo',
        'value': 'test'
    }
    resp = await client.post('/facts', json=fact_data, headers=headers)
    data = await resp.json()
    response = data['added']
    assert len(response) == 1
    assert response[0]['trait'] == 'demo'
    assert response[0]['value'] == 'test'

    tmp = await client.get('/facts', json=fact_data, headers=headers)
    cur = await tmp.json()
    current = cur['found']
    assert current == response


async def test_add_fact_to_operation(knowledge_webapp, aiohttp_client, test_operation, setup_empty_operation, fire_event_mock):
    client = await aiohttp_client(knowledge_webapp)

    fact_data = {
        'trait': 'demo',
        'value': 'test',
        'source': test_operation['id']
    }
    resp = await client.post('/facts', json=fact_data, headers=headers)
    data = await resp.json()
    response = data['added']
    assert len(response) == 1
    assert response[0]['trait'] == 'demo'
    assert response[0]['value'] == 'test'
    assert response[0]['source'] == test_operation['id']

    tmp = await client.get('/facts', json=fact_data, headers=headers)
    cur = await tmp.json()
    current = cur['found']
    assert current == response
    data_svc = BaseService.get_service('data_svc')
    file_svc = BaseService.get_service('file_svc')
    matched_operations = await data_svc.locate('operations', {'id': test_operation['id']})
    report = await matched_operations[0].report(file_svc, data_svc)
    assert response[0] in report['facts']


async def test_add_fact_to_finished_operation(knowledge_webapp, aiohttp_client, setup_finished_operation,
                                              finished_operation_payload, fire_event_mock):
    client = await aiohttp_client(knowledge_webapp)
    op_id = finished_operation_payload['id']
    matched_operations = await BaseService.get_service('data_svc').locate('operations', {'id': op_id})
    assert await matched_operations[0].is_finished()

    fact_data = {
        'trait': 'demo',
        'value': 'test',
        'source': op_id
    }
    resp = await client.post('/facts', json=fact_data, headers=headers)
    data = await resp.json()
    assert 'error' in data
    assert 'Cannot add fact to finished operation.' in data['error']


async def test_add_relationship(knowledge_webapp, aiohttp_client, fire_event_mock):
    client = await aiohttp_client(knowledge_webapp)
    fact_data_a = {
        'trait': 'a',
        'value': '1',
    }
    fact_data_b = {
        'trait': 'b',
        'value': '2'
    }
    relationship_data = {
        'source': fact_data_a,
        'edge': 'tango',
        'target': fact_data_b
    }
    expected_response = f"{fact_data_a['trait']}({fact_data_a['value']}) : " \
                        f"tango : {fact_data_b['trait']}({fact_data_b['value']})"
    resp = await client.post('/relationships', json=relationship_data, headers=headers)
    data = await resp.json()
    response = data['added']
    assert len(response) == 1
    assert response[0]['source']['trait'] == fact_data_a['trait']
    assert response[0]['target']['value'] == fact_data_b['value']
    assert response[0]['edge'] == 'tango'
    assert response[0]['source']['relationships'] == response[0]['target']['relationships']
    assert response[0]['source']['relationships'][0] == expected_response

    resp = await client.get('/relationships', json=relationship_data, headers=headers)
    cur = await resp.json()
    current = cur['found']
    assert current == response


async def test_patch_fact(knowledge_webapp, aiohttp_client, fire_event_mock):
    client = await aiohttp_client(knowledge_webapp)
    fact_data = {
        'trait': 'domain.user.name',
        'value': 'thomas'
    }
    patch_data = {
        "criteria": {
            "trait": "domain.user.name",
            "value": "thomas"},
        "updates": {
            "value": "jacobson"
        }
    }
    await client.post('/facts', json=fact_data, headers=headers)
    resp = await client.patch('/facts', json=patch_data, headers=headers)
    message = await resp.json()
    patched = message['updated']
    assert len(patched) == 1
    assert patched[0]['value'] == 'jacobson'

    tmp = await client.get('/facts', json=dict(trait='domain.user.name'), headers=headers)
    cur = await tmp.json()
    current = cur['found']
    assert len(current) == 1
    assert patched == current


async def test_patch_relationship(knowledge_webapp, aiohttp_client, fire_event_mock):
    client = await aiohttp_client(knowledge_webapp)
    relationship_data = {
        "source": {
            "trait": "domain.user.name",
            "value": "bobross"
        },
        "edge": "has_password",
        "target": {
            "trait": "domain.user.password",
            "value": "12345"
        }
    }
    patch_data = {
        "criteria": {
            "edge": "has_password",
            "source": {
                "value": "bobross"
            }
        },
        "updates": {
            "target": {
                "value": "54321"
            },
            "edge": "has_admin_password"
        }
    }
    await client.post('/relationships', json=relationship_data, headers=headers)
    resp = await client.patch('/relationships', json=patch_data, headers=headers)
    message = await resp.json()
    patched = message['updated']
    assert len(patched) == 1
    assert patched[0]['target']['value'] == '54321'
    assert patched[0]['source']['value'] == 'bobross'
    assert patched[0]['edge'] == 'has_admin_password'

    tmp = await client.get('/relationships', json=dict(edge='has_admin_password'), headers=headers)
    cur = await tmp.json()
    current = cur['found']
    assert len(current) == 1
    assert patched == current
