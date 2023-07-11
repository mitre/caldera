import pytest

from base64 import b64encode

from app.data_encoders.plain_text import PlainTextEncoder
from app.data_encoders.base64_basic import Base64Encoder


@pytest.fixture
def plaintext_encoder():
    return PlainTextEncoder()


@pytest.fixture
def base64_encoder():
    return Base64Encoder()


@pytest.fixture
def setup_data_encoders(event_loop, data_svc):
    event_loop.run_until_complete(data_svc._load_data_encoders([]))


@pytest.mark.usefixtures(
    'setup_data_encoders'
)
class TestDataEncoders:
    def test_retrieval(self, event_loop, data_svc):
        results = event_loop.run_until_complete(data_svc.locate('data_encoders', match=dict(name='plain-text')))
        assert len(results) == 1
        plaintext_encoder = results[0]
        assert plaintext_encoder and isinstance(plaintext_encoder, PlainTextEncoder)

        results = event_loop.run_until_complete(data_svc.locate('data_encoders', match=dict(name='base64')))
        assert len(results) == 1
        base64_encoder = results[0]
        assert base64_encoder and isinstance(base64_encoder, Base64Encoder)

    def test_plaintext_encoding(self, plaintext_encoder):
        data = b'this will be encoded/decoded in plaintext'
        encoded = plaintext_encoder.encode(data)
        assert encoded == data
        decoded = plaintext_encoder.decode(encoded)
        assert decoded == data

    def test_base64_encoding(self, base64_encoder):
        data = b'this will be encoded/decoded in base64'
        encoded = base64_encoder.encode(data)
        expected_encoded = b64encode(data)
        assert encoded == expected_encoded
        decoded = base64_encoder.decode(encoded)
        assert decoded == data
