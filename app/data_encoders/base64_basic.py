from base64 import b64encode, b64decode

from app.objects.c_data_encoder import DataEncoder


def load():
    return Base64Encoder()


class Base64Encoder(DataEncoder):
    def __init__(self):
        super().__init__('base64', 'Encodes and decodes data in base64')

    def encode(self, data, **_):
        """Returns base64 encoded data."""
        return b64encode(data)

    def decode(self, encoded_data, **_):
        """Returns b64 decoded bytes."""
        return b64decode(encoded_data)
