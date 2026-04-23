import os
import pytest
import yaml

from aiohttp import FormData
from http import HTTPStatus


@pytest.fixture
def valid_ability_yaml():
    ability_data = {
        'id': 'upload-test-001',
        'name': 'Uploaded Test Ability',
        'description': 'An ability uploaded via YAML file',
        'tactic': 'discovery',
        'technique_id': 'T1082',
        'technique_name': 'System Information Discovery',
        'executors': [
            {
                'name': 'sh',
                'platform': 'linux',
                'command': 'uname -a'
            }
        ]
    }
    yield yaml.dump([ability_data], sort_keys=False).encode('utf-8')

    # Cleanup
    path = 'data/abilities/discovery/upload-test-001.yml'
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass


@pytest.fixture
def valid_ability_yaml_with_ability_id_key():
    """Uses 'ability_id' key instead of 'id'."""
    ability_data = {
        'ability_id': 'upload-test-002',
        'name': 'Uploaded Test Ability 2',
        'description': 'An ability using ability_id key',
        'tactic': 'collection',
        'technique_id': 'T1005',
        'technique_name': 'Data from Local System',
        'executors': [
            {
                'name': 'sh',
                'platform': 'linux',
                'command': 'ls -la'
            }
        ]
    }
    yield yaml.dump([ability_data], sort_keys=False).encode('utf-8')

    path = 'data/abilities/collection/upload-test-002.yml'
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass


class TestAbilityUploadApi:

    async def test_upload_valid_yaml(self, api_v2_client, api_cookies, valid_ability_yaml):
        form = FormData()
        form.add_field('file', valid_ability_yaml,
                       filename='upload-test-001.yml',
                       content_type='application/x-yaml')
        resp = await api_v2_client.post('/api/v2/abilities/upload',
                                        cookies=api_cookies,
                                        data=form)
        assert resp.status == HTTPStatus.OK
        result = await resp.json()
        assert result['ability_id'] == 'upload-test-001'
        assert result['name'] == 'Uploaded Test Ability'
        assert result['tactic'] == 'discovery'
        assert os.path.exists('data/abilities/discovery/upload-test-001.yml')

    async def test_upload_valid_yaml_ability_id(self, api_v2_client, api_cookies, valid_ability_yaml_with_ability_id_key):
        form = FormData()
        form.add_field('file', valid_ability_yaml_with_ability_id_key,
                       filename='upload-test-001.yml',
                       content_type='application/x-yaml')
        resp = await api_v2_client.post('/api/v2/abilities/upload',
                                        cookies=api_cookies,
                                        data=form)
        assert resp.status == HTTPStatus.OK
        result = await resp.json()
        assert result['ability_id'] == 'upload-test-002'
        assert result['name'] == 'Uploaded Test Ability 2'
        assert result['tactic'] == 'collection'
        assert os.path.exists('data/abilities/collection/upload-test-002.yml')

    async def test_upload_invalid_file_type(self, api_v2_client, api_cookies):
        form = FormData()
        form.add_field('file', b'not yaml content',
                       filename='bad_file.txt',
                       content_type='text/plain')
        resp = await api_v2_client.post('/api/v2/abilities/upload',
                                        cookies=api_cookies,
                                        data=form)
        assert resp.status == HTTPStatus.BAD_REQUEST

    async def test_upload_malformed_yaml(self, api_v2_client, api_cookies):
        form = FormData()
        form.add_field('file', b'{{invalid: yaml: [}',
                       filename='malformed.yml',
                       content_type='application/x-yaml')
        resp = await api_v2_client.post('/api/v2/abilities/upload',
                                        cookies=api_cookies,
                                        data=form)
        assert resp.status == HTTPStatus.BAD_REQUEST

    async def test_upload_missing_required_fields(self, api_v2_client, api_cookies):
        incomplete = yaml.dump([{'description': 'no id, name, or tactic'}]).encode('utf-8')
        form = FormData()
        form.add_field('file', incomplete,
                       filename='incomplete.yml',
                       content_type='application/x-yaml')
        resp = await api_v2_client.post('/api/v2/abilities/upload',
                                        cookies=api_cookies,
                                        data=form)
        assert resp.status == HTTPStatus.BAD_REQUEST

    async def test_unauthorized_upload(self, api_v2_client, valid_ability_yaml):
        form = FormData()
        form.add_field('file', valid_ability_yaml,
                       filename='upload-test-001.yml',
                       content_type='application/x-yaml')
        resp = await api_v2_client.post('/api/v2/abilities/upload',
                                        data=form)
        assert resp.status == HTTPStatus.UNAUTHORIZED
