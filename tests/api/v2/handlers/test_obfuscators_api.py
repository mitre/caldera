import pytest

from http import HTTPStatus

from app.objects.c_obfuscator import Obfuscator
from app.utility.base_service import BaseService


@pytest.fixture
def test_obfuscator(event_loop, api_v2_client):
    obfuscator = Obfuscator(name='test', description='a test obfuscator', module='testmodule')
    event_loop.run_until_complete(BaseService.get_service('data_svc').store(obfuscator))
    return obfuscator


class TestObfuscatorsApi:
    async def test_get_obfuscators(self, api_v2_client, api_cookies, test_obfuscator):
        resp = await api_v2_client.get('/api/v2/obfuscators', cookies=api_cookies)
        obfuscators_list = await resp.json()
        assert len(obfuscators_list) == 1
        obfuscator_dict = obfuscators_list[0]
        assert obfuscator_dict == test_obfuscator.display_schema.dump(test_obfuscator)

    async def test_unauthorized_get_obfuscators(self, api_v2_client, test_obfuscator):
        resp = await api_v2_client.get('/api/v2/obfuscators')
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_get_obfuscator_by_id(self, api_v2_client, api_cookies, test_obfuscator):
        resp = await api_v2_client.get(f'/api/v2/obfuscators/{test_obfuscator.name}', cookies=api_cookies)
        obfuscator_dict = await resp.json()
        assert obfuscator_dict == test_obfuscator.display_schema.dump(test_obfuscator)

    async def test_unauthorized_get_obfuscator_by_id(self, api_v2_client, test_obfuscator):
        resp = await api_v2_client.get(f'/api/v2/obfuscators/{test_obfuscator.name}')
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_get_nonexistent_obfuscator_by_id(self, api_v2_client, api_cookies):
        resp = await api_v2_client.get('/api/v2/obfuscators/999', cookies=api_cookies)
        assert resp.status == HTTPStatus.NOT_FOUND
