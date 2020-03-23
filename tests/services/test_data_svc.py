import json
import pytest

from app.objects.c_ability import Ability
from app.objects.c_adversary import Adversary
from app.objects.c_agent import Agent
from app.objects.c_operation import Operation
from app.objects.c_planner import Planner
from tests.test_utils import temp_file


class TestDataService:

    def test_no_duplicate_adversary(self, loop, data_svc):
        loop.run_until_complete(data_svc.store(
            Adversary(adversary_id='123', name='test', description='test adversary', phases=dict())
        ))
        loop.run_until_complete(data_svc.store(
            Adversary(adversary_id='123', name='test', description='test adversary', phases=dict())
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
                    platform='darwin', payload='wifi.sh', parsers=[], requirements=[], privilege=None,
                    variations=[])
        ))
        loop.run_until_complete(data_svc.store(
            Ability(ability_id='123', tactic='discovery', technique_id='1', technique='T1033', name='test',
                    test='d2hvYW1pCg==', description='find active user', cleanup='', executor='sh',
                    platform='darwin', payload='wifi.sh', parsers=[], requirements=[], privilege=None,
                    variations=[])
        ))
        abilities = loop.run_until_complete(data_svc.locate('abilities'))

        assert len(abilities) == 1

    def test_operation(self, loop, data_svc):
        adversary = loop.run_until_complete(data_svc.store(
            Adversary(adversary_id='123', name='test', description='test adversary', phases=dict())
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

    def test_adversary_loading(self, loop, data_svc, file_svc):
        adversary1 = '''
---
id: 900DF00D-900D-F00D-900D-F00D900DF00D
name: test adversary
description: dont do much at all
phases:
  1:
    - c0da588f-79f0-4263-8998-7496b1a40596 #whoami?
        '''
        with temp_file('data/adversaries/900DF00D-900D-F00D-900D-F00D900DF00D.yml', adversary1):
            adversary = loop.run_until_complete(data_svc._grab_adversary(id='900DF00D-900D-F00D-900D-F00D900DF00D'))
            adversary_nextform = loop.run_until_complete(data_svc._load_adversary(adversary[0]))
            assert adversary_nextform['adversary_id'] == adversary[0]['id']
            assert all([isinstance(a, Ability) for phase in adversary_nextform['phases'] for a in phase])

    def test_adversary_loading_loop_check(self, loop, data_svc, file_svc):
        adversary1 = '''
---
id: DEADBEEF-DEAD-BEEF-DEAD-BEEFDEADBEEF
name: trouble seeker
description: throw an error
phases:
  1:
    - c0da588f-79f0-4263-8998-7496b1a40596 #whoami?
packs:
  - DEADBEEF-DEAD-BEEF-DEAD-BEEFDEADBEEF #ourself
        '''
        with temp_file('data/adversaries/DEADBEEF-DEAD-BEEF-DEAD-BEEFDEADBEEF.yml', adversary1):
            with pytest.raises(Exception, match=r".*infinite loop detected.*"):
                adversary = loop.run_until_complete(data_svc._grab_adversary(id='DEADBEEF-DEAD-BEEF-DEAD-BEEFDEADBEEF'))
                adversary_nextform = loop.run_until_complete(data_svc._load_adversary(adversary[0]))
                assert adversary_nextform
