import json

from app.objects.c_ability import Ability
from app.objects.c_adversary import Adversary
from app.objects.c_agent import Agent
from app.objects.c_operation import Operation
from app.objects.c_planner import Planner
from app.objects.secondclass.c_executor import Executor


class TestDataService:

    def test_no_duplicate_adversary(self, event_loop, data_svc):
        event_loop.run_until_complete(data_svc.store(
            Adversary(adversary_id='123', name='test', description='test adversary', atomic_ordering=list())
        ))
        event_loop.run_until_complete(data_svc.store(
            Adversary(adversary_id='123', name='test', description='test adversary', atomic_ordering=list())
        ))
        adversaries = event_loop.run_until_complete(data_svc.locate('adversaries'))

        assert len(adversaries) == 1
        for x in adversaries:
            json.dumps(x.display)

    def test_no_duplicate_planner(self, event_loop, data_svc):
        event_loop.run_until_complete(data_svc.store(Planner(name='test', planner_id='some_id', module='some.path.here', params=None, description='description')))
        event_loop.run_until_complete(data_svc.store(Planner(name='test', planner_id='some_id', module='some.path.here', params=None, description='description')))
        planners = event_loop.run_until_complete(data_svc.locate('planners'))

        assert len(planners) == 1
        for x in planners:
            json.dumps(x.display)

    def test_multiple_agents(self, event_loop, data_svc):
        event_loop.run_until_complete(data_svc.store(Agent(sleep_min=2, sleep_max=8, watchdog=0)))
        event_loop.run_until_complete(data_svc.store(Agent(sleep_min=2, sleep_max=8, watchdog=0)))
        agents = event_loop.run_until_complete(data_svc.locate('agents'))

        assert len(agents) == 2
        for x in agents:
            json.dumps(x.display)

    def test_no_duplicate_ability(self, event_loop, data_svc):
        executor = Executor(name='special_executor', platform='darwin', command='whoami', payloads=['wifi.sh'])
        event_loop.run_until_complete(data_svc.store(
            Ability(ability_id='123', tactic='discovery', technique_id='1', technique_name='T1033', name='test',
                    description='find active user', privilege=None, executors=[executor])
        ))
        event_loop.run_until_complete(data_svc.store(
            Ability(ability_id='123', tactic='discovery', technique_id='1', technique_name='T1033', name='test',
                    description='find active user', privilege=None, executors=[executor])
        ))
        abilities = event_loop.run_until_complete(data_svc.locate('abilities'))

        assert len(abilities) == 1

    def test_operation(self, event_loop, data_svc):
        adversary = event_loop.run_until_complete(data_svc.store(
            Adversary(adversary_id='123', name='test', description='test adversary', atomic_ordering=list())
        ))
        event_loop.run_until_complete(data_svc.store(Operation(name='my first op', agents=[], adversary=adversary)))

        operations = event_loop.run_until_complete(data_svc.locate('operations'))
        assert len(operations) == 1
        for x in operations:
            json.dumps(x.display)

    def test_remove(self, event_loop, data_svc):
        a1 = event_loop.run_until_complete(data_svc.store(Agent(sleep_min=2, sleep_max=8, watchdog=0)))
        agents = event_loop.run_until_complete(data_svc.locate('agents', match=dict(paw=a1.paw)))
        assert len(agents) == 1
        event_loop.run_until_complete(data_svc.remove('agents', match=dict(paw=a1.paw)))
        agents = event_loop.run_until_complete(data_svc.locate('agents', match=dict(paw=a1.paw)))
        assert len(agents) == 0

    def test_no_autogen_cleanup_cmds(self, event_loop, data_svc):
        cleanup_executor = Executor(name='sh', platform='linux', cleanup='rm #{payload}')
        event_loop.run_until_complete(data_svc.store(
            Ability(ability_id='4cd4eb44-29a7-4259-91ae-e457b283a880', tactic='defense-evasion', technique_id='T1070.004',
                    technique_name='Indicator Removal on Host: File Deletion', name='Delete payload',
                    description='Remove a downloaded payload file', privilege=None, executors=[cleanup_executor])
        ))
        executor = Executor(name='special_executor', platform='darwin', command='whoami', payloads=['wifi.sh'])
        event_loop.run_until_complete(data_svc.store(
            Ability(ability_id='123', tactic='discovery', technique_id='1', technique_name='T1033', name='test',
                    description='find active user', privilege=None, executors=[executor])
        ))
        event_loop.run_until_complete(data_svc._verify_abilities())
        abilities = event_loop.run_until_complete(data_svc.locate('abilities', dict(ability_id='123')))

        for ability in abilities:
            for executor in ability.executors:
                assert not executor.cleanup
