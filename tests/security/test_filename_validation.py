import unittest
from app.service.file_svc import FileSvc


class TestFilenameValidation(unittest.TestCase):
    def test_valid_filenames(self):
        self.assertTrue(FileSvc._validate_filename('test.ps1'))
        self.assertTrue(FileSvc._validate_filename('my-payload_v2.exe'))
        self.assertTrue(FileSvc._validate_filename('agent.bin'))

    def test_invalid_path_traversal(self):
        self.assertFalse(FileSvc._validate_filename('../../../etc/passwd'))
        self.assertFalse(FileSvc._validate_filename('..\\windows\\system32'))

    def test_invalid_null_byte(self):
        self.assertFalse(FileSvc._validate_filename('test\x00.ps1'))

    def test_invalid_special_chars(self):
        self.assertFalse(FileSvc._validate_filename('test file.ps1'))
        self.assertFalse(FileSvc._validate_filename('test;rm -rf /.ps1'))
        self.assertFalse(FileSvc._validate_filename('<script>.js'))

    def test_empty_filename(self):
        self.assertFalse(FileSvc._validate_filename(''))

    def test_too_long_filename(self):
        self.assertFalse(FileSvc._validate_filename('a' * 256))
        self.assertTrue(FileSvc._validate_filename('a' * 255))


if __name__ == '__main__':
    unittest.main()
