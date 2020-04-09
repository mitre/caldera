import json

from app.objects.c_ability import Ability
from app.objects.c_adversary import Adversary
from app.objects.c_agent import Agent
from app.objects.c_operation import Operation
from app.objects.c_planner import Planner


class TestDataService:

    def test_no_duplicate_adversary(self, loop, data_svc):
        loop.run_until_complete(data_svc.store(
            Adversary(adversary_id='123', name='test', description='test adversary', atomic_ordering=list())
        ))
        loop.run_until_complete(data_svc.store(
            Adversary(adversary_id='123', name='test', description='test adversary', atomic_ordering=list())
        ))
        adversaries = loop.run_until_complete(data_svc.locate('adversaries'))

        assert len(adversaries) == 1
        for x in adversaries:
            json.dumps(x.display)

    def test_no_duplicate_planner(self, loop, data_svc):
        loop.run_until_complete(data_svc.store(Planner(name='test', planner_id='some_id', module='some.path.here', params=None, description='description')))
        loop.run_until_complete(data_svc.store(Planner(name='test', planner_id='some_id', module='some.path.here', params=None, description='description')))
        planners = loop.run_until_complete(data_svc.locate('planners'))

        assert len(planners) == 1
        for x in planners:
            json.dumps(x.display)

    def test_multiple_agents(self, loop, data_svc):
        loop.run_until_complete(data_svc.store(Agent(sleep_min=2, sleep_max=8, watchdog=0)))
        loop.run_until_complete(data_svc.store(Agent(sleep_min=2, sleep_max=8, watchdog=0)))
        agents = loop.run_until_complete(data_svc.locate('agents'))

        assert len(agents) == 2
        for x in agents:
            json.dumps(x.display)

    def test_no_duplicate_ability(self, loop, data_svc):
        loop.run_until_complete(data_svc.store(
            Ability(ability_id='123', tactic='discovery', technique_id='1', technique='T1033', name='test',
                    test='d2hvYW1pCg==', description='find active user', cleanup='', executor='sh',
                    platform='darwin', payloads=['wifi.sh'], parsers=[], requirements=[], privilege=None,
                    variations=[])
        ))
        loop.run_until_complete(data_svc.store(
            Ability(ability_id='123', tactic='discovery', technique_id='1', technique='T1033', name='test',
                    test='d2hvYW1pCg==', description='find active user', cleanup='', executor='sh',
                    platform='darwin', payloads=['wifi.sh'], parsers=[], requirements=[], privilege=None,
                    variations=[])
        ))
        abilities = loop.run_until_complete(data_svc.locate('abilities'))

        assert len(abilities) == 1

    def test_operation(self, loop, data_svc):
        adversary = loop.run_until_complete(data_svc.store(
            Adversary(adversary_id='123', name='test', description='test adversary', atomic_ordering=list())
        ))
        loop.run_until_complete(data_svc.store(Operation(name='my first op', agents=[], adversary=adversary)))

        operations = loop.run_until_complete(data_svc.locate('operations'))
        assert len(operations) == 1
        for x in operations:
            json.dumps(x.display)

    def test_remove(self, loop, data_svc):
        a1 = loop.run_until_complete(data_svc.store(Agent(sleep_min=2, sleep_max=8, watchdog=0)))
        agents = loop.run_until_complete(data_svc.locate('agents', match=dict(paw=a1.paw)))
        assert len(agents) == 1
        loop.run_until_complete(data_svc.remove('agents', match=dict(paw=a1.paw)))
        agents = loop.run_until_complete(data_svc.locate('agents', match=dict(paw=a1.paw)))
        assert len(agents) == 0
