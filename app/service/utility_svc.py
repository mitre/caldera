from base64 import b64encode, b64decode
from random import randint

import yaml

from app.utility.logger import Logger
from app.utility.stealth import obfuscate_ps1, obfuscate_bash


class UtilityService:

    @staticmethod
    def apply_stealth(executor, code):
        options = dict(windows=lambda c: obfuscate_ps1(c),
                       darwin=lambda c: obfuscate_bash(c),
                       linux=lambda c: obfuscate_bash(c))
        return options[executor](code)

    @staticmethod
    def decode_bytes(s):
        return b64decode(s).decode('utf-8').replace('\n','')

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
            with open(path) as seed:
                return list(yaml.load_all(seed))
        return []

    @staticmethod
    def write_yaml(path, data):
        with open(path, 'w+') as yaml_file:
            yaml.dump(data, yaml_file, default_flow_style=False)
