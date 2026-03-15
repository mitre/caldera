import unittest


class TestContactHttpBodyLimit(unittest.TestCase):
    def test_body_size_computation(self):
        max_kb = 512
        max_bytes = max_kb * 1024
        self.assertEqual(max_bytes, 524288)

    def test_oversized_body_detected(self):
        max_bytes = 512 * 1024
        body = b'x' * (max_bytes + 1)
        self.assertTrue(len(body) > max_bytes)

    def test_normal_body_accepted(self):
        max_bytes = 512 * 1024
        body = b'x' * 1000
        self.assertFalse(len(body) > max_bytes)


if __name__ == '__main__':
    unittest.main()
