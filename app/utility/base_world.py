import binascii
import string
import os
import yaml
import logging

from base64 import b64encode, b64decode
from datetime import datetime
from importlib import import_module
from random import randint, choice
from enum import Enum


class BaseWorld:
    """
    A collection of base static functions for service & object module usage
    """

    _app_configuration = None

    @staticmethod
    def apply_config(config):
        BaseWorld._app_configuration = config

    @staticmethod
    def get_config(prop=None):
        if prop:
            return BaseWorld._app_configuration.get(prop)
        return BaseWorld._app_configuration

    @staticmethod
    def set_config(prop, value):
        BaseWorld._app_configuration[prop] = value

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
    async def walk_file_path(path, target):
        for root, dirs, files in os.walk(path):
            if target in files:
                return os.path.join(root, target)
            if '%s.xored' % target in files:
                return os.path.join(root, '%s.xored' % target)
        return None

    class Access(Enum):
        APP = 0
        RED = 1
        BLUE = 2
