import pytest

from http import HTTPStatus

from app.objects.c_plugin import Plugin
from app.utility.base_service import BaseService


@pytest.fixture
def test_plugin(event_loop, api_v2_client):
    plugin = Plugin(name="test_plugin", enabled=True, description="a test plugin", address="test_address")
    event_loop.run_until_complete(BaseService.get_service('data_svc').store(plugin))
    return plugin


@pytest.fixture
def expected_test_plugin_dump(test_plugin):
    return test_plugin.display_schema.dump(test_plugin)


class TestPluginsApi:
    async def test_get_plugins(self, api_v2_client, api_cookies, test_plugin, expected_test_plugin_dump):
        resp = await api_v2_client.get('/api/v2/plugins', cookies=api_cookies)
        plugins_list = await resp.json()
        assert len(plugins_list) == 1
        plugin_dict = plugins_list[0]
        assert plugin_dict == expected_test_plugin_dump

    async def test_unauthorized_get_plugins(self, api_v2_client, test_plugin):
        resp = await api_v2_client.get('/api/v2/plugins')
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_get_plugin_by_id(self, api_v2_client, api_cookies, test_plugin, expected_test_plugin_dump):
        resp = await api_v2_client.get(f'/api/v2/plugins/{test_plugin.name}', cookies=api_cookies)
        plugin_dict = await resp.json()
        assert plugin_dict == expected_test_plugin_dump

    async def test_unauthorized_get_plugin_by_id(self, api_v2_client, test_plugin):
        resp = await api_v2_client.get(f'/api/v2/plugins/{test_plugin.name}')
        assert resp.status == HTTPStatus.UNAUTHORIZED

    async def test_get_nonexistent_plugin_by_id(self, api_v2_client, api_cookies):
        resp = await api_v2_client.get('/api/v2/plugins/999', cookies=api_cookies)
        assert resp.status == HTTPStatus.NOT_FOUND
