import unittest
from app.service.utility_svc import UtilityService

class TestUtilityService(unittest.TestCase):

    # Tests that the encode string function correctly encodes
    def test_encode_string(self):
        self.assertEqual(UtilityService.encode_string("this is a super string!"),"dGhpcyBpcyBhIHN1cGVyIHN0cmluZyE=")

    # Tests that the decode string function correctly decodes
    def test_decode_string(self):
        self.assertEqual(UtilityService.decode_bytes("Ynl0ZXMgdGhhdCBJIG5lZWQgZGVjb2RlZCEgSGVyZSBhcmUgdGhlIGJ5dGVzLiA="),
                                                     "bytes that I need decoded! Here are the bytes. ")

    # Tests if the encode and decode string functions can encode and decode a string to the original value
    def test_decode_encode_string_functional(self):
        mystring = "Speedily say has suitable disposal add boy. On forth doubt miles of child. Exercise joy man " \
                   "children rejoiced. Yet uncommonly his ten who diminution astonished. Demesne new manners " \
                   "savings staying had. Under folly balls death own point now men. Match way these she avoid " \
                   "see death. She whose drift their fat off. "
        self.assertEqual(UtilityService.decode_bytes(UtilityService.encode_string(mystring)),mystring)

