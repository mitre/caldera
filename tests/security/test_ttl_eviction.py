import datetime
import unittest
from unittest.mock import MagicMock


class TestTTLEviction(unittest.TestCase):
    def test_old_operations_evicted(self):
        """Test that finished operations older than TTL are evicted."""
        ttl = 7 * 86400  # 7 days in seconds
        now = datetime.datetime.utcnow()

        old_op = MagicMock()
        old_op.finish = 'some-time'
        old_op.start = now - datetime.timedelta(days=10)

        new_op = MagicMock()
        new_op.finish = 'some-time'
        new_op.start = now - datetime.timedelta(days=1)

        running_op = MagicMock()
        running_op.finish = None
        running_op.start = now - datetime.timedelta(days=30)

        operations = [old_op, new_op, running_op]
        filtered = [
            op for op in operations
            if not (getattr(op, 'finish', None) and
                    hasattr(op, 'start') and op.start and
                    (now - op.start).total_seconds() > ttl)
        ]
        self.assertEqual(len(filtered), 2)  # new_op and running_op
        self.assertIn(new_op, filtered)
        self.assertIn(running_op, filtered)
        self.assertNotIn(old_op, filtered)


if __name__ == '__main__':
    unittest.main()
