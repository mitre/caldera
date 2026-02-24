import logging
import pathlib
import secrets

import jinja2
import yaml

from argon2 import PasswordHasher


CONFIG_MSG_TEMPLATE = jinja2.Template("""
Log into Caldera with the following admin credentials:
    Red:
    {%- if users.red.red %}
        USERNAME: red
        PASSWORD: {{ users.red.red }}
    {%- endif %}
        API_TOKEN: {{ api_key_red }}
    Blue:
    {%- if users.blue.blue %}
        USERNAME: blue
        PASSWORD: {{ users.blue.blue }}
    {%- endif %}
        API_TOKEN: {{ api_key_blue }}
To modify these values, edit the {{ config_path }} file and restart Caldera.
""")
LOCAL_CONF_PATH = 'conf/local.yml'
SECRET_OPTIONS = ('api_key_blue', 'api_key_red', 'crypt_salt', 'encryption_key')
HASHED_OPTIONS = ('api_key_blue', 'api_key_red')


def _is_hashed(val):
    return val.startswith('$argon2id$')


def hash_config_creds(config):
    """
    Hashes the red/blue API keys and any user passwords in the config dictionary.
    Modifies the configuration dictionary parameter.
    Returns True if any values were modified (hashed), False otherwise.
    """
    ph = PasswordHasher()
    any_hashed = False
    for option in HASHED_OPTIONS:
        val = config.get(option, '')

        # Skip any values that are already hashed
        if val and not _is_hashed(val):
            config[option] = ph.hash(val)
            any_hashed = True

    # Hash credentials
    for group_name, group_dict in config.get('users', dict()).items():
        for username, val in group_dict.items():
            if not _is_hashed(val):
                config['users'][group_name][username] = ph.hash(val)
                any_hashed = True

    return any_hashed


def make_secure_config():
    with open('conf/default.yml', 'r') as fle:
        config = yaml.safe_load(fle)

    for option in SECRET_OPTIONS:
        config[option] = secrets.token_urlsafe()

    config['users'] = dict(red=dict(red=secrets.token_urlsafe()),
                           blue=dict(blue=secrets.token_urlsafe()))

    # Display API keys and user credentials, then hash them
    logging.info(CONFIG_MSG_TEMPLATE.render(config_path=LOCAL_CONF_PATH, **config))
    hash_config_creds(config)

    return config


def ensure_local_config():
    """
    Checks if a local.yml config file exists. If not, generates a new local.yml file using secure random values.
    """
    local_conf_path = pathlib.Path(LOCAL_CONF_PATH)
    if local_conf_path.exists():
        return

    logging.info('Creating new secure config in %s' % local_conf_path)
    with local_conf_path.open('w') as fle:
        yaml.safe_dump(make_secure_config(), fle, default_flow_style=False)
