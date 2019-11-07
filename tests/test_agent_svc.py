import time
import unittest

from app.service.agent_svc import AgentService
from app.service.data_svc import DataService
from tests.test_base import TestBase


class TestAgent(TestBase):

    def setUp(self):
        self.data_svc = DataService()
        self.agent_svc = AgentService()

    def test_heartbeat(self):
        agent_details = dict(
            paw='bab90a6d-6ad7-45af-aab0-e2c2951f7bf8', platform='windows', server='http://localhost:8888',
            host='test', username='user', group='my_group', executors='psh,cmd', architecture=None, location=None,
            pid=1000, ppid=1, sleep=60, privilege=None
        )
        t1 = self.run_async(self.agent_svc.handle_heartbeat(**agent_details)).last_seen
        self.assertEqual(1, len(self.data_svc.ram['agents']))
        time.sleep(2)
        t2 = self.run_async(self.agent_svc.handle_heartbeat(**agent_details)).last_seen
        self.assertEqual(1, len(self.data_svc.ram['agents']))
        self.assertTrue(t2 > t1)

    def test_instructions(self):
        i = self.run_async(self.agent_svc.get_instructions('bab90a6d-6ad7-45af-aab0-e2c2951f7bf8'))
        self.assertEqual(i, '[]')


if __name__ == '__main__':
    unittest.main()
