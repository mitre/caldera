import unittest

from app.service.base_service import BaseService


class TestUtilityService(unittest.TestCase):
    def test_encode_string(self):
        self.assertEqual(BaseService.encode_string('this is a super string!'), 'dGhpcyBpcyBhIHN1cGVyIHN0cmluZyE=')

    def test_decode_string(self):
        self.assertEqual(BaseService.decode_bytes('Ynl0ZXMgdGhhdCBJIG5lZWQgZGVjb2RlZCEgSGVyZSBhcmUgdGhlIGJ5dGVzLiA='),
                         'bytes that I need decoded! Here are the bytes. ')

    def test_decode_encode_string_functional(self):
        my_string = '“Enough! Breach this firewall with your viral energies or suffer! Your choice." - Megabyte'
        self.assertEqual(BaseService.decode_bytes(BaseService.encode_string(my_string)), my_string)
