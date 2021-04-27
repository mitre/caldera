from app.utility.base_world import BaseWorld


class DataEncoding(BaseWorld):
    def encode(self, data, **_):
        return data

    def decode(self, data, **k_):
        return data
