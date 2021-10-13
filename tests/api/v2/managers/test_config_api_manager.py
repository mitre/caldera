import pytest

from app.api.v2 import errors
from app.api.v2.managers import config_api_manager
from app.api.v2.managers.config_api_manager import ConfigApiManager, ConfigNotFound, ConfigUpdateNotAllowed
from app.utility.base_world import BaseWorld


class StubDataService:
    def __init__(self,):
        self.abilities = []

    async def locate(self, key):
        assert key == 'abilities'
        return self.abilities


@pytest.fixture
def base_world(app_config, agent_config):
    BaseWorld.clear_config()
    BaseWorld.apply_config('main', app_config)
    BaseWorld.apply_config('agents', agent_config)

    yield BaseWorld

    BaseWorld.clear_config()


def test_filter_keys():
    mapping = {
        'foo': 1,
        'bar': 2,
        'baz': {
            'key3': 3,
            'key4': 4
        }
    }

    filtered = config_api_manager.filter_keys(mapping, keys_to_remove=['baz', 'bar'])
    expected = {'foo': 1}
    assert filtered == expected


def test_get_filtered_config_remove_sensitive_keys(base_world, data_svc):
    test_conf = {
        'users': 'this should be filtered',
        'host': 'this should be filtered',
        'foo': '1',
        'bar': '2',
        'baz': '3'
    }
    base_world.apply_config('test', test_conf)

    manager = ConfigApiManager(data_svc, None)
    filtered = manager.get_filtered_config('test')
    expected = {
        'foo': '1',
        'bar': '2',
        'baz': '3'
    }

    assert filtered == expected


def test_get_filtered_config_all_sensitive_keys_filtered(base_world, data_svc):
    sensitive_conf = {key: 'foo' for key in config_api_manager.SENSITIVE_CONFIG_PROPS}
    base_world.apply_config('test', sensitive_conf)
    assert base_world.get_config(name='test') == sensitive_conf

    manager = ConfigApiManager(data_svc, None)
    filtered = manager.get_filtered_config('test')
    assert filtered == {}


def test_get_filtered_config_throws_exception_on_not_found(base_world, data_svc):
    manager = ConfigApiManager(data_svc, None)

    with pytest.raises(ConfigNotFound):
        manager.get_filtered_config('THIS DOES NOT EXIST')


def test_update_main_config(base_world, data_svc):
    manager = ConfigApiManager(data_svc, None)
    manager.update_main_config(prop='foo.bar', value=100)
    assert manager.get_filtered_config('main')['foo.bar'] == 100


def test_update_main_config_throws_exception_on_sensitive_field(base_world, data_svc):
    manager = ConfigApiManager(data_svc, None)

    with pytest.raises(ConfigUpdateNotAllowed):
        manager.update_main_config(prop='host', value='this is not allowed')


async def test_update_global_agent_config(base_world, data_svc):
    manager = ConfigApiManager(data_svc, None)
    await manager.update_global_agent_config(sleep_min=5, sleep_max=10)

    agent_config = manager.get_filtered_config('agents')
    assert agent_config['sleep_min'] == 5
    assert agent_config['sleep_max'] == 10


async def test_update_global_agent_config_allows_partial_updates(base_world, data_svc):
    manager = ConfigApiManager(data_svc, None)
    agent_config = manager.get_filtered_config('agents')

    await manager.update_global_agent_config()  # no arguments passed in--should no-op
    assert manager.get_filtered_config('agents') == agent_config


async def test_update_global_agent_config_updates_list_properties(base_world, ability):
    stub_data_svc = StubDataService()
    stub_data_svc.abilities = [
        ability('ability-1'),
        ability('ability-2'),
        ability('ability-3')
    ]

    manager = ConfigApiManager(data_svc=stub_data_svc, file_svc=None)
    await manager.update_global_agent_config(
        deadman_abilities=['ability-1', 'ability-2'],
        bootstrap_abilities=['ability-3']
    )

    agent_config = manager.get_filtered_config('agents')
    assert agent_config['deadman_abilities'] == ['ability-1', 'ability-2']
    assert agent_config['bootstrap_abilities'] == ['ability-3']


async def test_update_global_agent_config_throws_validation_error_bad_sleep_min(base_world, data_svc):
    manager = ConfigApiManager(data_svc, None)

    with pytest.raises(errors.DataValidationError):
        await manager.update_global_agent_config(sleep_min=-1)


async def test_update_global_agent_config_throws_validation_error_bad_sleep_max(base_world, data_svc):
    manager = ConfigApiManager(data_svc, None)

    with pytest.raises(errors.DataValidationError):
        await manager.update_global_agent_config(sleep_max=-1)


async def test_update_global_agent_config_throws_validation_error_bad_watchdog(base_world, data_svc):
    manager = ConfigApiManager(data_svc, None)

    with pytest.raises(errors.DataValidationError):
        await manager.update_global_agent_config(watchdog=-1)


async def test_update_global_agent_config_throws_validation_error_bad_untrusted_timer(base_world, data_svc):
    manager = ConfigApiManager(data_svc, None)

    with pytest.raises(errors.DataValidationError):
        await manager.update_global_agent_config(untrusted_timer=-1)


async def test_update_global_agent_config_throws_validation_error_bad_implant_name(base_world, data_svc):
    manager = ConfigApiManager(data_svc, None)

    with pytest.raises(errors.DataValidationError):
        await manager.update_global_agent_config(implant_name='')


async def test_update_main_config_throws_validation_error_empty_prop(base_world, data_svc):
    manager = ConfigApiManager(data_svc, None)

    with pytest.raises(errors.DataValidationError):
        await manager.update_main_config(prop='', value=1234)
