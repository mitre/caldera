import json
import unittest

from app.objects.c_ability import Ability
from app.objects.c_adversary import Adversary
from app.objects.c_agent import Agent
from app.objects.c_executor import Executor
from app.objects.c_operation import Operation
from app.objects.c_planner import Planner
from app.service.data_svc import DataService
from tests.test_base import TestBase


class TestData(TestBase):

    def setUp(self):
        self.data_svc = DataService()

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
        self.run_async(self.data_svc.store(Planner(name='test', module='some.path.here', params=None)))
        self.run_async(self.data_svc.store(Planner(name='test', module='some.path.here', params=None)))
        planners = self.run_async(self.data_svc.locate('planners'))

        self.assertEqual(1, len(planners))
        for x in planners:
            json.dumps(x.display)

    def test_agent(self):
        self.run_async(self.data_svc.store(Agent(paw='123$abc')))
        self.run_async(self.data_svc.store(Agent(paw='123$abc')))
        agents = self.run_async(self.data_svc.locate('agents'))

        self.assertEqual(1, len(agents))
        for x in agents:
            json.dumps(x.display)

    def test_ability(self):
        self.run_async(self.data_svc.store(
            Ability(ability_id='123', tactic='discovery', technique_id='1', technique='T1033', name='test',
                    test='whoami', description='find active user', cleanup='', executor='sh',
                    platform='darwin', payload='wifi.sh', parsers=[], requirements=[], privilege=None)
        ))
        self.run_async(self.data_svc.store(
            Ability(ability_id='123', tactic='discovery', technique_id='1', technique='T1033', name='test',
                    test='whoami', description='find active user', cleanup='', executor='sh',
                    platform='darwin', payload='wifi.sh', parsers=[], requirements=[], privilege=None)
        ))
        abilities = self.run_async(self.data_svc.locate('abilities'))

        self.assertEqual(1, len(abilities))
        for x in abilities:
            json.dumps(x.display)

    def test_operation(self):
        adversary = self.run_async(self.data_svc.store(
            Adversary(adversary_id='123', name='test', description='test adversary', phases=dict())
        ))
        self.run_async(self.data_svc.store(Operation(op_id=1, name='my first op', agents=[], adversary=adversary)))
        operations = self.run_async(self.data_svc.locate('operations'))
        self.assertEqual(1, len(operations))

        self.run_async(self.data_svc.store(Operation(op_id=2, name='my first op', agents=[], adversary=adversary)))
        operations = self.run_async(self.data_svc.locate('operations'))

        self.assertEqual(2, len(operations))
        for x in operations:
            json.dumps(x.display)

    def test_executor(self):
        x = Executor(name='sh', preferred=1)
        self.assertRaises(Exception, self.run_async(self.data_svc.store(x)))


if __name__ == '__main__':
    unittest.main()
