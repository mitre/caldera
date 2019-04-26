from base64 import b64encode, b64decode
from random import randint


class UtilityService:

    @staticmethod
    def decode_bytes(s):
        return b64decode(s).decode('utf-8')

    @staticmethod
    def encode_string(s):
        return str(b64encode(s.encode()), 'utf-8')

    @staticmethod
    def jitter(fraction):
        i = fraction.split('/')
        return randint(int(i[0]), int(i[1]))
