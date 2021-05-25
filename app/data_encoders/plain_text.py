from app.objects.c_data_encoder import DataEncoder


def load():
    return PlainTextEncoder()


class PlainTextEncoder(DataEncoder):
    def __init__(self):
        super().__init__('plain-text',
                         'Does not encode or decode data at all, instead keeps it in plain text form')

    def encode(self, data, **_):
        return data

    def decode(self, encoded_data, **_):
        return encoded_data
