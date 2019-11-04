import json
import unittest

from app.objects.c_ability import Ability
from app.objects.c_adversary import Adversary
from app.objects.c_agent import Agent
from app.objects.c_operation import Operation
from app.objects.c_planner import Planner
from app.service.data_svc import DataService
from tests.test_base import TestBase


class TestObjects(TestBase):

    def setUp(self):
        self.data_svc = DataService()

    def test_adversary(self):
        self.run_async(self.data_svc.store(
            Adversary(adversary_id='123', name='test', description='test adversary', phases=dict())
        ))
        self.assertEqual(1, len(self.data_svc.ram['adversaries']))
        for x in self.data_svc.ram['adversaries']:
            json.dumps(x.display)

    def test_planner(self):
        self.run_async(self.data_svc.store(
            Planner(name='test', module='some.path.here', params=None)
        ))
        self.assertEqual(1, len(self.data_svc.ram['planners']))
        for x in self.data_svc.ram['planners']:
            json.dumps(x.display)

    def test_agent(self):
        self.run_async(self.data_svc.store(
            Agent(paw='123$abc')
        ))
        self.assertEqual(1, len(self.data_svc.ram['agents']))
        for x in self.data_svc.ram['agents']:
            json.dumps(x.display)

    def test_ability(self):
        self.run_async(self.data_svc.store(
            Ability(ability_id='123', tactic='discovery', technique_id='1', technique='T1033', name='test',
                    test='whoami', description='find active user', cleanup='', executor='sh',
                    platform='darwin', payload='wifi.sh', parsers=[], requirements=[])
        ))
        self.assertEqual(1, len(self.data_svc.ram['abilities']))
        for x in self.data_svc.ram['abilities']:
            json.dumps(x.display)

    def test_operation(self):
        adversary = self.run_async(self.data_svc.store(
            Adversary(adversary_id='123', name='test', description='test adversary', phases=dict())
        ))
        self.run_async(self.data_svc.store(
            Operation(op_id=1, name='my first op', agents=[], adversary=adversary)
        ))
        self.assertEqual(1, len(self.data_svc.ram['operations']))
        for x in self.data_svc.ram['operations']:
            json.dumps(x.display)


if __name__ == '__main__':
    unittest.main()
