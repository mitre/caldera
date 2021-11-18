import binascii
import string
import re
import yaml
import logging
import subprocess
import distutils.version
from base64 import b64encode, b64decode
from datetime import datetime, timezone
from importlib import import_module
from random import randint, choice
from enum import Enum

import marshmallow as ma
import marshmallow_enum as ma_enum


class BaseWorld:
    """
    A collection of base static functions for service & object module usage
    """

    _app_configuration = dict()

    re_base64 = re.compile('[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', flags=re.DOTALL)
    TIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'

    @staticmethod
    def apply_config(name, config):
        BaseWorld._app_configuration[name] = config

    @staticmethod
    def clear_config():
        BaseWorld._app_configuration = {}

    @staticmethod
    def get_config(prop=None, name=None):
        name = name if name else 'main'
        if prop:
            return BaseWorld._app_configuration[name].get(prop)
        return BaseWorld._app_configuration[name]

    @staticmethod
    def set_config(name, prop, value):
        if value is not None:
            logging.debug('Configuration (%s) update, setting %s=%s' % (name, prop, value))
            BaseWorld._app_configuration[name][prop] = value

    @staticmethod
    def decode_bytes(s, strip_newlines=True):
        decoded = b64decode(s).decode('utf-8', errors='ignore')
        return decoded.replace('\r\n', '').replace('\n', '') if strip_newlines else decoded

    @staticmethod
    def encode_string(s):
        return str(b64encode(s.encode()), 'utf-8')

    @staticmethod
    def jitter(fraction):
        i = fraction.split('/')
        return randint(int(i[0]), int(i[1]))

    @staticmethod
    def create_logger(name):
        return logging.getLogger(name)

    @staticmethod
    def strip_yml(path):
        if path:
            with open(path, encoding='utf-8') as seed:
                return list(yaml.load_all(seed, Loader=yaml.FullLoader))
        return []

    @staticmethod
    def prepend_to_file(filename, line):
        with open(filename, 'r+') as f:
            content = f.read()
            f.seek(0, 0)
            f.write(line.rstrip('\r\n') + '\n' + content)

    @staticmethod
    def get_current_timestamp(date_format=TIME_FORMAT):
        return datetime.now(timezone.utc).strftime(date_format)

    @staticmethod
    def get_timestamp_from_string(datetime_str, date_format=TIME_FORMAT):
        return datetime.strptime(datetime_str, date_format)

    @staticmethod
    async def load_module(module_type, module_info):
        module = import_module(module_info['module'])
        return getattr(module, module_type)(module_info)

    @staticmethod
    def generate_name(size=16):
        return ''.join(choice(string.ascii_lowercase) for _ in range(size))

    @staticmethod
    def generate_number(size=6):
        return randint((10 ** (size - 1)), ((10 ** size) - 1))

    @staticmethod
    def is_base64(s):
        try:
            b64decode(s, validate=True)
            return True
        except binascii.Error:
            return False

    @staticmethod
    def is_uuid4(s):
        if BaseWorld.re_base64.match(s):
            return True
        return False

    @staticmethod
    def check_requirement(params):
        def check_module_version(module, version, attr=None, **kwargs):
            attr = attr if attr else '__version__'
            mod_version = getattr(import_module(module), attr, '')
            return compare_versions(mod_version, version)

        def check_program_version(command, version, **kwargs):
            output = subprocess.check_output(command.split(' '), stderr=subprocess.STDOUT, shell=False, timeout=10)
            return compare_versions(output.decode('utf-8'), version)

        def compare_versions(version_string, minimum_version):
            version = parse_version(version_string)
            return distutils.version.StrictVersion(version) >= distutils.version.StrictVersion(str(minimum_version))

        def parse_version(version_string, pattern=r'([0-9]+(?:\.[0-9]+)+)'):
            groups = re.search(pattern, version_string)
            if groups:
                return groups[1]
            return '0.0.0'

        checkers = dict(
            python_module=check_module_version,
            installed_program=check_program_version
        )

        try:
            requirement_type = params.get('type')
            return checkers[requirement_type](**params)
        except FileNotFoundError:
            return False
        except Exception as e:
            logging.getLogger('check_requirement').error(repr(e))
            return False

    class Access(Enum):
        APP = 0
        RED = 1
        BLUE = 2
        HIDDEN = 3

    class Privileges(Enum):
        User = 0
        Elevated = 1


class AccessSchema(ma.Schema):
    access = ma_enum.EnumField(BaseWorld.Access)


class PrivilegesSchema(ma.Schema):
    privilege = ma_enum.EnumField(BaseWorld.Privileges)
