import logging
import pathlib
import secrets

import jinja2
import yaml


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
To modify these values, edit the {{ config_path }} file.
""")


def log_config_message(config_path):
    with pathlib.Path(config_path).open('r') as fle:
        config = yaml.safe_load(fle)
    logging.info(CONFIG_MSG_TEMPLATE.render(config_path=str(config_path), **config))


def make_secure_config():
    with open('conf/default.yml', 'r') as fle:
        config = yaml.safe_load(fle)

    secret_options = ('api_key_blue', 'api_key_red', 'crypt_salt', 'encryption_key')
    for option in secret_options:
        config[option] = secrets.token_urlsafe()

    config['users'] = dict(red=dict(red=secrets.token_urlsafe()),
                           blue=dict(blue=secrets.token_urlsafe()))

    return config


def ensure_local_config():
    """
    Checks if a local.yml config file exists. If not, generates a new local.yml file using secure random values.
    """
    local_conf_path = pathlib.Path('conf/local.yml')
    if local_conf_path.exists():
        return

    logging.info('Creating new secure config in %s' % local_conf_path)
    with local_conf_path.open('w') as fle:
        yaml.safe_dump(make_secure_config(), fle, default_flow_style=False)

    log_config_message(local_conf_path)
