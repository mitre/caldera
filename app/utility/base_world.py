import binascii
import string
import os
import re
import yaml
import logging
import subprocess
import distutils.version

import dirhash

from base64 import b64encode, b64decode
from datetime import datetime
from importlib import import_module
from random import randint, choice
from enum import Enum


class BaseWorld:
    """
    A collection of base static functions for service & object module usage
    """

    _app_configuration = dict()

    re_base64 = re.compile('[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', flags=re.DOTALL)

    @staticmethod
    def apply_config(name, config):
        BaseWorld._app_configuration[name] = config

    @staticmethod
    def get_config(prop=None, name=None):
        name = name if name else 'default'
        if prop:
            return BaseWorld._app_configuration[name].get(prop)
        return BaseWorld._app_configuration[name]

    @staticmethod
    def set_config(name, prop, value):
        if value is not None:
            logging.debug('Configuration (%s) update, setting %s=%s' % (name, prop, value))
            BaseWorld._app_configuration[name][prop] = value

    @staticmethod
    def decode_bytes(s):
        return b64decode(s).decode('utf-8', errors='ignore').replace('\n', '')

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
    def get_current_timestamp(date_format='%Y-%m-%d %H:%M:%S'):
        return datetime.now().strftime(date_format)

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
    async def walk_file_path(path, target):
        for root, _, files in os.walk(path):
            if target in files:
                return os.path.join(root, target)
            if '%s.xored' % target in files:
                return os.path.join(root, '%s.xored' % target)
        return None

    @staticmethod
    def check_requirement(params):
        def check_module_version(module, version, attr=None, **kwargs):
            attr = attr if attr else '__version__'
            mod_version = getattr(import_module(module), attr, '')
            return compare_versions(mod_version, version)

        def check_program_version(command, version, **kwargs):
            output = subprocess.check_output(command.split(' '), shell=False)
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
        except Exception as e:
            logging.getLogger('check_requirement').error(repr(e))

    @staticmethod
    def get_version(path='.'):
        ignore = ['/plugins/', '/.tox/']
        included_extensions = ['*.py', '*.html', '*.js', '*.go']
        version_file = os.path.join(path, 'VERSION.txt')
        if os.path.exists(version_file):
            with open(version_file, 'r') as f:
                version, md5 = f.read().strip().split('-')
            calculated_md5 = dirhash.dirhash(path, 'md5', ignore=ignore, match=included_extensions)
            if md5 == calculated_md5:
                return version
        return None

    class Access(Enum):
        APP = 0
        RED = 1
        BLUE = 2

    class Privileges(Enum):
        User = 0
        Elevated = 1
