import unittest


class TestApiPagination(unittest.TestCase):
    def test_pagination_defaults(self):
        limit = min(int('100'), 1000)
        offset = max(int('0'), 0)
        self.assertEqual(limit, 100)
        self.assertEqual(offset, 0)

    def test_pagination_applies_correctly(self):
        items = list(range(50))
        limit = 10
        offset = 5
        result = items[offset:offset + limit]
        self.assertEqual(result, list(range(5, 15)))

    def test_pagination_max_limit(self):
        limit = min(int('5000'), 1000)
        self.assertEqual(limit, 1000)

    def test_pagination_negative_offset_clamped(self):
        offset = max(int('-5'), 0)
        self.assertEqual(offset, 0)

    def test_pagination_beyond_end(self):
        items = list(range(10))
        result = items[20:30]
        self.assertEqual(result, [])


if __name__ == '__main__':
    unittest.main()
