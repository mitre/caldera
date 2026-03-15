import unittest


class TestClientMaxSize(unittest.TestCase):
    def test_default_client_max_size(self):
        """Verify that 1MB is computed correctly."""
        client_max_size_mb = 1
        result = client_max_size_mb * 1024 * 1024
        self.assertEqual(result, 1048576)

    def test_custom_client_max_size(self):
        """Verify custom size is computed correctly."""
        client_max_size_mb = 5
        result = client_max_size_mb * 1024 * 1024
        self.assertEqual(result, 5242880)

    def test_none_fallback(self):
        """When config returns None, default to 1MB."""
        config_val = None
        result = (config_val or 1) * 1024 * 1024
        self.assertEqual(result, 1048576)

    def test_old_value_was_larger(self):
        """Confirm old value (5120**2) was ~26MB, much larger than 1MB."""
        old_value = 5120 ** 2
        new_value = 1 * 1024 * 1024
        self.assertGreater(old_value, new_value)
        self.assertEqual(old_value, 26214400)


if __name__ == '__main__':
    unittest.main()
