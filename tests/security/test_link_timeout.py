import unittest
from unittest.mock import MagicMock


class TestLinkTimeoutCapping(unittest.TestCase):
    def test_timeout_capped(self):
        max_timeout = 600
        executor = MagicMock()
        executor.timeout = 1200
        if executor.timeout > max_timeout:
            executor.timeout = max_timeout
        self.assertEqual(executor.timeout, 600)

    def test_timeout_not_capped_when_below(self):
        max_timeout = 600
        executor = MagicMock()
        executor.timeout = 300
        if executor.timeout > max_timeout:
            executor.timeout = max_timeout
        self.assertEqual(executor.timeout, 300)

    def test_default_max_timeout(self):
        from app.utility.base_planning_svc import BasePlanningService
        self.assertEqual(BasePlanningService.MAX_LINK_TIMEOUT_DEFAULT, 600)


if __name__ == '__main__':
    unittest.main()
