from base64 import b64encode, b64decode

from app.utility.base_world import BaseWorld


class DataEncoding(BaseWorld):
    def encode(self, data, **_):
        """
        Returns base64 bytes of data
        """
        return b64encode(data)

    def decode(self, encoded_data, **_):
        """
        Returns b64 decoded bytes.
        """
        return b64decode(encoded_data)
