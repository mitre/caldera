import os
import pytest

from http import HTTPStatus

from app.utility.base_service import BaseService


def ability_file_cleanup(tactic, ability_id):
    file_path = f'data/abilities/{tactic}/{ability_id}.yml'
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError:
            pass


def basic_ability(identifier_key, identifier, name, description, tactic):
    return {
        identifier_key: identifier,
        'name': name,
        'description': description,
        'tactic': tactic,
        'technique': {
            'attack_id': 'T1083',
            'name': 'File and Directory Discovery'
        },
        'platforms': {
            'darwin': {
                'sh': {
                    'command': 'ls #{host.system.path}'
                }
            },
            'linux': {
                'sh': {
                    'command': 'ls #{host.system.path}'
                }
            },
            'windows': {
                'psh': {
                    'command': 'dir #{host.system.path}'
                }
            }
        },
        'requirements': [
            {
                'plugins.stockpile.app.requirements.paw_provenance': [
                    {
                        'source': 'host.system.path'
                    }
                ]
            }
        ]
    }


@pytest.fixture
def valid_ability_payload():
    yield basic_ability(
        'id',
        'upload-test-001',
        'Uploaded Test Ability',
        'An ability uploaded via YAML file',
        'discovery'
    )

    ability_file_cleanup('discovery', 'upload-test-001')


@pytest.fixture
def valid_ability_payload_with_ability_id():
    yield basic_ability(
        'ability_id',
        'upload-test-002',
        'Uploaded Test Ability 2',
        'An ability using ability_id key',
        'collection'
    )

    ability_file_cleanup('collection', 'upload-test-002')


class TestAbilityUploadApi:

    async def test_create_ability_from_yaml_style_payload(self, api_v2_client, api_cookies, valid_ability_payload):
        resp = await api_v2_client.post('/api/v2/abilities', cookies=api_cookies, json=valid_ability_payload)

        assert resp.status == HTTPStatus.OK
        result = await resp.json()
        assert result['ability_id'] == 'upload-test-001'
        assert result['name'] == 'Uploaded Test Ability'
        assert result['tactic'] == 'discovery'
        assert result['technique_id'] == 'T1083'
        assert result['technique_name'] == 'File and Directory Discovery'
        assert {executor['platform'] for executor in result['executors']} == {'darwin', 'linux', 'windows'}
        assert os.path.exists('data/abilities/discovery/upload-test-001.yml')

        ability = (await BaseService.get_service('data_svc').locate(
            'abilities', {'ability_id': 'upload-test-001'}
        ))[0]
        assert ability.requirements[0].module == 'plugins.stockpile.app.requirements.paw_provenance'

    async def test_create_ability_from_yaml_style_payload_with_ability_id(
            self, api_v2_client, api_cookies, valid_ability_payload_with_ability_id
    ):
        resp = await api_v2_client.post('/api/v2/abilities', cookies=api_cookies,
                                        json=valid_ability_payload_with_ability_id)

        assert resp.status == HTTPStatus.OK
        result = await resp.json()
        assert result['ability_id'] == 'upload-test-002'
        assert result['name'] == 'Uploaded Test Ability 2'
        assert result['tactic'] == 'collection'
        assert os.path.exists('data/abilities/collection/upload-test-002.yml')

    async def test_create_ability_from_yaml_style_payload_missing_required_fields(self, api_v2_client, api_cookies):
        resp = await api_v2_client.post('/api/v2/abilities', cookies=api_cookies,
                                        json={'description': 'no name, tactic, or executor configuration'})

        assert resp.status == HTTPStatus.BAD_REQUEST

    async def test_unauthorized_create_ability_from_yaml_style_payload(self, api_v2_client, valid_ability_payload):
        resp = await api_v2_client.post('/api/v2/abilities', json=valid_ability_payload)

        assert resp.status == HTTPStatus.UNAUTHORIZED
