from typing import List

from app.api.v2 import validation
from app.api.v2.managers.base_api_manager import BaseApiManager
from app.utility.base_world import BaseWorld


SENSITIVE_CONFIG_PROPS = frozenset([
    'api_key_blue',
    'api_key_red',
    'auth.login.handler.module',
    'crypt_salt',
    'encryption_key',
    'host',
    'port',
    'requirements',
    'users'
])


def filter_keys(mapping, keys_to_remove):
    filtered = {}

    for key, val in mapping.items():
        if key not in keys_to_remove:
            filtered[key] = val

    return filtered


def filter_sensitive_props(config_map):
    """Return a copy of `config_map` with top-level sensitive keys removed."""
    return filter_keys(config_map, keys_to_remove=SENSITIVE_CONFIG_PROPS)


def is_sensitive_prop(prop):
    """Return True if the input prop is a sensitive configuration property."""
    return prop in SENSITIVE_CONFIG_PROPS


class ConfigUpdateNotAllowed(Exception):
    def __init__(self, property, message=None):
        super().__init__(message or f'Updating property is disallowed: {property}')
        self.property = property


class ConfigNotFound(Exception):
    def __init__(self, config_name, message=None):
        super().__init__(message or f'Config not found: {config_name}')
        self.config_name = config_name


class ConfigApiManager(BaseApiManager):
    def __init__(self, data_svc, file_svc, config_interface=None):
        super().__init__(data_svc=data_svc, file_svc=file_svc)
        self._config_interface = config_interface or BaseWorld

    def get_filtered_config(self, name):
        """Return the configuration for the input `name` with sensitive fields removed."""
        try:
            config = self._config_interface.get_config(name=name)
        except KeyError:
            raise ConfigNotFound(name)
        return filter_sensitive_props(config)

    def update_main_config(self, prop, value):
        validation.check_not_empty_string(prop, name='prop')

        if is_sensitive_prop(prop):
            raise ConfigUpdateNotAllowed(prop)

        if prop == 'plugin':
            enabled_plugins = self._config_interface.get_config(
                name='main',
                prop='plugins'
            )

            if value not in enabled_plugins:
                enabled_plugins.append(value)
        else:
            self._config_interface.set_config(
                name='main',
                prop=prop,
                value=value
            )

    async def update_global_agent_config(self, sleep_min: int = None, sleep_max: int = None, watchdog: int = None,
                                         untrusted_timer: int = None, implant_name: str = None, bootstrap_abilities: List[str] = None, deadman_abilities=None):
        set_config = self._config_interface.set_config

        if sleep_min is not None:
            validation.check_positive_integer(sleep_min, name='sleep_min')
            set_config(name='agents', prop='sleep_min', value=sleep_min)
        if sleep_max is not None:
            validation.check_positive_integer(sleep_max, name='sleep_max')
            set_config(name='agents', prop='sleep_max', value=sleep_max)
        if untrusted_timer is not None:
            validation.check_positive_integer(untrusted_timer, name='untrusted_timer')
            set_config(name='agents', prop='untrusted_timer', value=untrusted_timer)
        if watchdog is not None:
            validation.check_positive_integer(watchdog, name='watchdog')
            set_config(name='agents', prop='watchdog', value=watchdog)
        if implant_name is not None:
            validation.check_not_empty_string(implant_name, name='implant_name')
            set_config(name='agents', prop='implant_name', value=implant_name)
        if bootstrap_abilities is not None:
            await self._update_agent_ability_list_property(bootstrap_abilities, 'bootstrap_abilities')
        if deadman_abilities is not None:
            await self._update_agent_ability_list_property(deadman_abilities, 'deadman_abilities')

    async def _get_loaded_ability_ids(self):
        return set(x.ability_id for x in await self._data_svc.locate('abilities'))

    async def _update_agent_ability_list_property(self, ability_id_list, prop):
        """Set the specified agent config property with the specified abilities."""
        abilities_to_set = []
        loaded_ability_ids = await self._get_loaded_ability_ids()

        for ability_id in ability_id_list:
            ability_id = ability_id.strip()

            if not ability_id:
                continue
            elif ability_id in loaded_ability_ids:
                abilities_to_set.append(ability_id)
            else:
                self.log.debug('Could not find ability with id "%s"', ability_id)

        self._config_interface.set_config(name='agents', prop=prop, value=abilities_to_set)
