import unittest

from app.service.utility_svc import UtilityService


class TestUtilityService(unittest.TestCase):
    def test_encode_string(self):
        self.assertEqual(UtilityService.encode_string('this is a super string!'),'dGhpcyBpcyBhIHN1cGVyIHN0cmluZyE=')

    def test_decode_string(self):
        self.assertEqual(UtilityService.decode_bytes('Ynl0ZXMgdGhhdCBJIG5lZWQgZGVjb2RlZCEgSGVyZSBhcmUgdGhlIGJ5dGVzLiA='),
                                                     'bytes that I need decoded! Here are the bytes. ')

    def test_decode_encode_string_functional(self):
        mystring = 'Speedily say has suitable disposal add boy. On forth doubt miles of child. Exercise joy man.'
        self.assertEqual(UtilityService.decode_bytes(UtilityService.encode_string(mystring)),mystring)

