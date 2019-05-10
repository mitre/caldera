from base64 import b64encode, b64decode
from random import randint

from app.utility.stealth import obfuscate_ps1, obfuscate_bash


class UtilityService:

    @staticmethod
    def apply_stealth(executor, code):
        options = dict(psh=lambda c: obfuscate_ps1(c), bash=lambda c: obfuscate_bash(c))
        return options[executor](code)

    @staticmethod
    def decode_bytes(s):
        return b64decode(s).decode('utf-8').replace("\n","")

    @staticmethod
    def encode_string(s):
        return str(b64encode(s.encode()), 'utf-8')

    @staticmethod
    def jitter(fraction):
        i = fraction.split('/')
        return randint(int(i[0]), int(i[1]))
