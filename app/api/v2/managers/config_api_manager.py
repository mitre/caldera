import logging

from app.utility.base_world import BaseWorld


SENSITIVE_CONFIG_PROPS = frozenset([
    'ability_refresh',
    'api_key_blue',
    'api_key_red',
    'app.contact.gist',
    'app.contact.tunnel.ssh.host_key_file',
    'app.contact.tunnel.ssh.host_key_passphrase',
    'app.contact.tunnel.ssh.user_name',
    'app.contact.tunnel.ssh.user_password',
    'crypt_salt',
    'encryption_key',
    'host',
    'port',
    'requirements',
    'users'
])


def filter_sensitive_props(config_map):
    """Return a copy of `config_map` with top-level sensitive keys removed."""
    filtered = {}

    for key, val in config_map.items():
        if key not in SENSITIVE_CONFIG_PROPS:
            filtered[key] = val

    return filtered


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


class ConfigApiManager:
    def __init__(self, services, config_interface=None):
        self._config_interface = config_interface or BaseWorld
        self._data_svc = services['data_svc']
        self._log = logging.getLogger('config_api_manager')

    def get_filtered_config(self, name):
        """Return the configuration for the input `name` with sensitive fields removed."""
        try:
            config = self._config_interface.get_config(name=name)
        except KeyError:
            raise ConfigNotFound(name)
        return filter_sensitive_props(config)

    def update_main_config(self, prop, value):
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

    async def update_global_agent_config(self, sleep_min=None, sleep_max=None, watchdog=None, untrusted_timer=None,
                                         implant_name=None, bootstrap_abilities=None, deadman_abilities=None):

        set_config = self._config_interface.set_config

        if sleep_min is not None:
            set_config(name='agents', prop='sleep_min', value=sleep_min)
        if sleep_max is not None:
            set_config(name='agents', prop='sleep_max', value=sleep_max)
        if untrusted_timer is not None:
            set_config(name='agents', prop='untrusted_timer', value=untrusted_timer)
        if watchdog is not None:
            set_config(name='agents', prop='watchdog', value=watchdog)
        if implant_name is not None:
            set_config(name='agents', prop='implant_name', value=implant_name)
        if bootstrap_abilities is not None:
            await self._update_agent_ability_list_property(bootstrap_abilities, 'bootstrap_abilities')
        if deadman_abilities is not None:
            await self._update_agent_ability_list_property(deadman_abilities, 'deadman_abilities')

    async def _update_agent_ability_list_property(self, ability_id_list, prop):
        """Set the specified agent config property with the specified abilities."""
        abilities = []
        loaded_ability_ids = set(x.ability_id for x in await self._data_svc.locate('abilities'))

        for ability_id in ability_id_list:
            ability_id = ability_id.strip()

            if not ability_id:
                continue
            elif ability_id in loaded_ability_ids:
                abilities.append(ability_id)
            else:
                self._log.debug('Could not find ability with id "%s"', ability_id)

        self._config_interface.set_config(name='agents', prop=prop, value=abilities)
