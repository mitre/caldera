import pytest

from base64 import b64decode
from app.objects.secondclass.c_link import Link
from app.obfuscators.plain_text import Obfuscation


@pytest.fixture
def plaintext_obfuscator(test_agent):
    return Obfuscation(test_agent)


class TestPlainTextObfuscator:
    def test_plaintext_obfuscator(self, plaintext_obfuscator, finished_link):
        link = Link.load(finished_link)
        plaintext_cmd = b64decode(link.command).decode('utf-8')
        decoded = plaintext_obfuscator.run(link)
        assert decoded == plaintext_cmd
