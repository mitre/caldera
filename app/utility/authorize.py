import os

from cryptography.exceptions import InvalidKey
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


_backend = default_backend()


class Authorize:

    @staticmethod
    async def registration_salt_key(password):
        salt = os.urandom(16)
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000, backend=_backend)
        return salt, kdf.derive(password.encode())

    @staticmethod
    async def verify(glob, key, salt):
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000, backend=_backend)
        try:
            kdf.verify(glob, key)
            return True
        except InvalidKey:
            return False
