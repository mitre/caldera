import json

from app.objects.c_ability import Ability
from app.objects.c_adversary import Adversary
from app.objects.c_agent import Agent
from app.objects.c_operation import Operation
from app.objects.c_planner import Planner
from tests.base.test_base import TestBase


class TestDataService(TestBase):

    def test_adversary(self, data_svc):
        self.run_async(data_svc.store(
            Adversary(adversary_id='123', name='test', description='test adversary', phases=dict())
        ))
        self.run_async(data_svc.store(
            Adversary(adversary_id='123', name='test', description='test adversary', phases=dict())
        ))
        adversaries = self.run_async(data_svc.locate('adversaries'))

        assert len(adversaries) == 1
        for x in adversaries:
            json.dumps(x.display)

    def test_planner(self, data_svc):
        self.run_async(data_svc.store(Planner(name='test', planner_id='some_id', module='some.path.here', params=None, description='description')))
        self.run_async(data_svc.store(Planner(name='test', planner_id='some_id', module='some.path.here', params=None, description='description')))
        planners = self.run_async(data_svc.locate('planners'))

        assert len(planners) == 1
        for x in planners:
            json.dumps(x.display)

    def test_agent(self, data_svc):
        self.run_async(data_svc.store(Agent(sleep_min=2, sleep_max=8, watchdog=0)))
        self.run_async(data_svc.store(Agent(sleep_min=2, sleep_max=8, watchdog=0)))
        agents = self.run_async(data_svc.locate('agents'))

        assert len(agents) == 2
        for x in agents:
            json.dumps(x.display)

    def test_ability(self, data_svc):
        self.run_async(data_svc.store(
            Ability(ability_id='123', tactic='discovery', technique_id='1', technique='T1033', name='test',
                    test='d2hvYW1pCg==', description='find active user', cleanup='', executor='sh',
                    platform='darwin', payload='wifi.sh', parsers=[], requirements=[], privilege=None,
                    variations=[])
        ))
        self.run_async(data_svc.store(
            Ability(ability_id='123', tactic='discovery', technique_id='1', technique='T1033', name='test',
                    test='d2hvYW1pCg==', description='find active user', cleanup='', executor='sh',
                    platform='darwin', payload='wifi.sh', parsers=[], requirements=[], privilege=None,
                    variations=[])
        ))
        abilities = self.run_async(data_svc.locate('abilities'))

        assert len(abilities) == 1

    def test_operation(self, data_svc):
        adversary = self.run_async(data_svc.store(
            Adversary(adversary_id='123', name='test', description='test adversary', phases=dict())
        ))
        self.run_async(data_svc.store(Operation(name='my first op', agents=[], adversary=adversary)))

        operations = self.run_async(data_svc.locate('operations'))
        assert len(operations) == 1
        for x in operations:
            json.dumps(x.display)

    def test_remove(self, data_svc):
        a1 = self.run_async(data_svc.store(Agent(sleep_min=2, sleep_max=8, watchdog=0)))
        agents = self.run_async(data_svc.locate('agents', match=dict(paw=a1.paw)))
        assert len(agents) == 1
        self.run_async(data_svc.remove('agents', match=dict(paw=a1.paw)))
        agents = self.run_async(data_svc.locate('agents', match=dict(paw=a1.paw)))
        assert len(agents) == 0
