import json
import unittest

from app.objects.c_ability import Ability
from app.objects.c_adversary import Adversary
from app.objects.c_agent import Agent
from app.objects.c_operation import Operation
from app.objects.c_planner import Planner
from tests.base.test_base import TestBase


class TestDataService(TestBase):

    def setUp(self):
        self.initialize()

    def test_adversary(self):
        self.run_async(self.data_svc.store(
            Adversary(adversary_id='123', name='test', description='test adversary', phases=dict())
        ))
        self.run_async(self.data_svc.store(
            Adversary(adversary_id='123', name='test', description='test adversary', phases=dict())
        ))
        adversaries = self.run_async(self.data_svc.locate('adversaries'))

        self.assertEqual(1, len(adversaries))
        for x in adversaries:
            json.dumps(x.display)

    def test_planner(self):
        self.run_async(self.data_svc.store(Planner(name='test', planner_id='some_id', module='some.path.here', params=None, description='description')))
        self.run_async(self.data_svc.store(Planner(name='test', planner_id='some_id', module='some.path.here', params=None, description='description')))
        planners = self.run_async(self.data_svc.locate('planners'))

        self.assertEqual(1, len(planners))
        for x in planners:
            json.dumps(x.display)

    def test_agent(self):
        self.run_async(self.data_svc.store(Agent(sleep_min=2, sleep_max=8, watchdog=0)))
        self.run_async(self.data_svc.store(Agent(sleep_min=2, sleep_max=8, watchdog=0)))
        agents = self.run_async(self.data_svc.locate('agents'))

        self.assertEqual(2, len(agents))
        for x in agents:
            json.dumps(x.display)

    def test_ability(self):
        self.run_async(self.data_svc.store(
            Ability(ability_id='123', tactic='discovery', technique_id='1', technique='T1033', name='test',
                    test='d2hvYW1pCg==', description='find active user', cleanup='', executor='sh',
                    platform='darwin', payload='wifi.sh', parsers=[], requirements=[], privilege=None)
        ))
        self.run_async(self.data_svc.store(
            Ability(ability_id='123', tactic='discovery', technique_id='1', technique='T1033', name='test',
                    test='d2hvYW1pCg==', description='find active user', cleanup='', executor='sh',
                    platform='darwin', payload='wifi.sh', parsers=[], requirements=[], privilege=None)
        ))
        abilities = self.run_async(self.data_svc.locate('abilities'))

        self.assertEqual(1, len(abilities))

    def test_operation(self):
        adversary = self.run_async(self.data_svc.store(
            Adversary(adversary_id='123', name='test', description='test adversary', phases=dict())
        ))
        self.run_async(self.data_svc.store(Operation(name='my first op', agents=[], adversary=adversary)))

        operations = self.run_async(self.data_svc.locate('operations'))
        self.assertEqual(1, len(operations))
        for x in operations:
            json.dumps(x.display)

    def test_remove(self):
        a1 = self.run_async(self.data_svc.store(Agent(sleep_min=2, sleep_max=8, watchdog=0)))
        agents = self.run_async(self.data_svc.locate('agents', match=dict(paw=a1.paw)))
        self.assertEqual(1, len(agents))
        self.run_async(self.data_svc.remove('agents', match=dict(paw=a1.paw)))
        agents = self.run_async(self.data_svc.locate('agents', match=dict(paw=a1.paw)))
        self.assertEqual(0, len(agents))


if __name__ == '__main__':
    unittest.main()
