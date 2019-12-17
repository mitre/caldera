from base64 import b64encode, b64decode
from datetime import datetime
from importlib import import_module
from random import randint, choice

import yaml
import string

from app.utility.logger import Logger


class BaseWorld:
    """
    A collection of base static functions for service & object module usage
    """

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
        return Logger(name)

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
    def decode(encoded_cmd, agent, group, reserved_words):
        decoded_cmd = b64decode(encoded_cmd).decode('utf-8', errors='ignore').replace('\n', '')
        decoded_cmd = decoded_cmd.replace(reserved_words['server'], agent.server)
        decoded_cmd = decoded_cmd.replace(reserved_words['group'], group)
        decoded_cmd = decoded_cmd.replace(reserved_words['paw'], agent.paw)
        decoded_cmd = decoded_cmd.replace(reserved_words['location'], agent.location)
        decoded_cmd = decoded_cmd.replace(reserved_words['exe_name'], agent.exe_name)
        return decoded_cmd

    @staticmethod
    async def load_module(module_type, module_info):
        module = import_module(module_info['module'])
        return getattr(module, module_type)(module_info)

    @staticmethod
    def generate_name(size=16):
        return ''.join(choice(string.ascii_lowercase) for _ in range(size))
