from base64 import b64encode, b64decode
from random import randint
from datetime import datetime

import yaml

from app.utility.logger import Logger
from app.utility.stealth import obfuscate_ps1, obfuscate_bash


class BaseService:

    _services = dict()

    def add_service(self, name: str, svc: 'BaseService') -> Logger:
        self.__class__._services[name] = svc
        return Logger(name)

    @classmethod
    def get_service(cls, name):
        return cls._services.get(name)

    @classmethod
    def get_services(cls):
        return cls._services

    @staticmethod
    def apply_stealth(executor, code):
        options = dict(windows=lambda c: obfuscate_ps1(c),
                       darwin=lambda c: obfuscate_bash(c),
                       linux=lambda c: obfuscate_bash(c))
        return options[executor](code)

    @staticmethod
    def decode_bytes(s):
        return b64decode(s).decode('utf-8').replace('\n', '')

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
                return list(yaml.load_all(seed))
        return []

    @staticmethod
    def write_yaml(path, data):
        with open(path, 'w+') as yaml_file:
            yaml.dump(data, yaml_file, default_flow_style=False)

    @staticmethod
    def prepend_to_file(filename, line):
        with open(filename, 'r+') as f:
            content = f.read()
            f.seek(0, 0)
            f.write(line.rstrip('\r\n') + '\n' + content)

    @staticmethod
    def get_current_timestamp(date_format='%Y-%m-%d %H:%M:%S'):
        return datetime.now().strftime(date_format)
