import pytest

from app.objects.c_adversary import Adversary
from app.objects.c_obfuscator import Obfuscator
from app.objects.c_source import Source
from app.objects.secondclass.c_link import Link
from app.utility.base_world import BaseWorld


@pytest.fixture
def setup_planning_test(loop, ability, agent, operation, data_svc, init_base_world):
    tability = ability(ability_id='123', executor='sh', platform='darwin', test=BaseWorld.encode_string('mkdir test'),
                       cleanup=BaseWorld.encode_string('rm -rf test'), variations=[])
    tagent = agent(sleep_min=1, sleep_max=2, watchdog=0, executors=['sh'], platform='darwin')
    tsource = Source(id='123', name='test', facts=[], adjustments=[])
    toperation = operation(name='test1', agents=tagent, adversary=Adversary(name='test', description='test',
                                                                            atomic_ordering=[], adversary_id='XYZ'),
                           source=tsource)

    loop.run_until_complete(data_svc.store(tability))

    loop.run_until_complete(data_svc.store(
        Obfuscator(name='plain-text',
                   description='Does no obfuscation to any command, instead running it in plain text',
                   module='plugins.stockpile.app.obfuscators.plain_text')
    ))

    yield tability, tagent, toperation


class TestPlanningService:

    def test_add_ability_to_bucket(self, loop, setup_planning_test, planning_svc):
        b1 = 'salvador'
        b2 = 'hardin'
        a, _, _ = setup_planning_test
        loop.run_until_complete(planning_svc.add_ability_to_bucket(a, b1))
        assert a.buckets == [b1]
        loop.run_until_complete(planning_svc.add_ability_to_bucket(a, b2))
        assert a.buckets == [b1, b2]

    def test_default_next_bucket(self, loop, planning_svc):
        sm = ['alpha', 'bravo', 'charlie']
        assert loop.run_until_complete(planning_svc.default_next_bucket(sm[0], sm)) == sm[1]
        assert loop.run_until_complete(planning_svc.default_next_bucket(sm[1], sm)) == sm[2]
        assert loop.run_until_complete(planning_svc.default_next_bucket(sm[2], sm)) == sm[0]    # loops around

    def test_stopping_condition_met(self, loop, planning_svc, fact):
        facts = [
            fact(trait='m.b.k', value='michael'),
            fact(trait='l.r.k', value='laura')
        ]
        stopping_condition = fact(trait='c.p.k', value='cole')

        assert loop.run_until_complete(planning_svc._stopping_condition_met(facts, stopping_condition)) is False
        facts.append(stopping_condition)
        assert loop.run_until_complete(planning_svc._stopping_condition_met(facts, stopping_condition)) is True

    def test_check_stopping_conditions(self, loop, fact, link, setup_planning_test, planning_svc):
        ability, agent, operation = setup_planning_test
        operation.source.facts = []
        stopping_conditions = [fact(trait='s.o.f.', value='seldon')]

        # first verify stopping conditions not met
        assert loop.run_until_complete(planning_svc.check_stopping_conditions(stopping_conditions, operation)) is False
        # add stopping condition to a fact, then to a link, then the link to the operation
        l0 = link(command='test', paw='0', ability=ability)
        l1 = link(command='test1', paw='1', ability=ability)
        loop.run_until_complete(l1._save_fact(operation, stopping_conditions[0], 1))  # directly attach fact to link
        operation.add_link(l0)
        operation.add_link(l1)
        # now verify stopping condition is met since we directly inserted fact that matches stopping conidition
        assert loop.run_until_complete(planning_svc.check_stopping_conditions(stopping_conditions, operation)) is True

    def test_update_stopping_condition_met(self, loop, fact, link, setup_planning_test, planning_svc):
        ability, agent, operation = setup_planning_test
        stopping_condition = fact(trait='t.c.t', value='boss')

        class PlannerStub():
            stopping_conditions = [stopping_condition]
            stopping_condition_met = False
        p = PlannerStub()

        # first call should not result in 'met' flag being flipped
        loop.run_until_complete(planning_svc.update_stopping_condition_met(p, operation))
        assert p.stopping_condition_met is False
        # add stopping condition to a fact, then to a link, then the link to the operation
        l1 = link(command='test1', paw='1', ability=ability)
        loop.run_until_complete(l1._save_fact(operation, stopping_condition, 1))  # directly attach fact to link
        operation.add_link(l1)
        # now verify stopping condition is met since we directly inserted fact that matches stopping conidition
        loop.run_until_complete(planning_svc.update_stopping_condition_met(p, operation))
        assert p.stopping_condition_met is True

    def test_sort_links(self, loop, link, planning_svc, setup_planning_test):
        a, _, _ = setup_planning_test
        l1 = link(command='m', paw='1', ability=a, score=1)
        l2 = link(command='a', paw='2', ability=a, score=2)
        l3 = link(command='l', paw='3', ability=a, score=3)
        sl = loop.run_until_complete(planning_svc.sort_links([l2, l1, l3]))
        assert sl[0] == l3
        assert sl[1] == l2
        assert sl[2] == l1

    def test_stop_bucket_execution(self, loop, setup_planning_test, planning_svc):
        ability, agent, operation = setup_planning_test

        class PlannerStub:
            stopping_condition_met = False

        p = PlannerStub()
        operation.state = operation.states['RUNNING']

        # case 1 - operation running, planner stop condition not met
        assert loop.run_until_complete(planning_svc._stop_bucket_exhaustion(p, operation, True)) is False
        # case 2 - operation running, planner stop condition met
        p.stopping_condition_met = True
        assert loop.run_until_complete(planning_svc._stop_bucket_exhaustion(p, operation, True)) is True
        # case 3 - operaton finished, planner stop condition not met
        operation.state = operation.states['FINISHED']
        p.stopping_condition_met = False
        assert loop.run_until_complete(planning_svc._stop_bucket_exhaustion(p, operation, True)) is True
        # case 4 - operation finished, planner stop condition met
        p.stopping_condition_met = True
        assert loop.run_until_complete(planning_svc._stop_bucket_exhaustion(p, operation, True)) is True
        # case 5 - case 2 with condition stop off
        operation.state = operation.states['RUNNING']
        assert loop.run_until_complete(planning_svc._stop_bucket_exhaustion(p, operation, False)) is False

    def test_execute_planner(self, loop, fact, link, setup_planning_test, planning_svc, monkeypatch):
        ability, agent, operation = setup_planning_test
        sc = fact(trait='j.g.b', value='good')

        class PlannerFake:
            def __init__(self, operation):
                self.state_machine = ['one', 'two', 'three', 'four']
                self.next_bucket = 'one'
                self.stopping_condition_met = False
                self.stopping_conditions = [sc]
                self.calls = []
                self.operation = operation

            async def one(self):
                self.calls.append('one')
                self.next_bucket = 'two'

            async def two(self):
                self.calls.append('two')
                self.next_bucket = 'three'

            async def three(self):
                self.calls.append('three')
                self.next_bucket = None  # stopping execution here

            async def four(self):
                self.calls.append('four')
                self.next_bucket = None

        # case 1 - let planner run until it stops itself after bucket 'three'
        p = PlannerFake(operation)
        loop.run_until_complete(planning_svc.execute_planner(p))
        assert p.calls == ['one', 'two', 'three']

        # case 2 - start planner but then hijack operation after bucket 'two and flag that stopping condition
        # been found, thus stopping the planner when it attempt to proceed to next bucket
        async def stub_update_stopping_condition_met(planner, operation):
            if planner.calls == ['one', 'two']:
                planner.stopping_condition_met = True
        monkeypatch.setattr(planning_svc, 'update_stopping_condition_met', stub_update_stopping_condition_met)
        p = PlannerFake(operation)
        loop.run_until_complete(planning_svc.execute_planner(p))
        assert p.calls == ['one', 'two']

        # case 3 - start planner but then hijack operation and set it to 'FINISH' state, thus
        # stopping the planner when it attempts to proceed to next bucket
        async def stub_update_stopping_condition_met_1(planner, operation):
            if planner.calls == ['one']:
                operation.state = operation.states['FINISHED']
        monkeypatch.setattr(planning_svc, 'update_stopping_condition_met', stub_update_stopping_condition_met_1)
        p = PlannerFake(operation)
        loop.run_until_complete(planning_svc.execute_planner(p))
        assert p.calls == ['one']

    def test_get_cleanup_links(self, loop, setup_planning_test, planning_svc):
        ability, agent, operation = setup_planning_test
        operation.add_link(Link.load(dict(command='', paw=agent.paw, ability=ability, status=0)))
        links = loop.run_until_complete(
            planning_svc.get_cleanup_links(operation=operation, agent=agent)
        )
        link_list = list(links)
        assert len(link_list) == 1
        assert link_list[0].command == ability.cleanup[0]

    def test_generate_and_trim_links(self, loop, setup_planning_test, planning_svc):
        ability, agent, operation = setup_planning_test
        generated_links = loop.run_until_complete(planning_svc.generate_and_trim_links(agent, operation, [ability]))
        assert 1 == len(generated_links)
