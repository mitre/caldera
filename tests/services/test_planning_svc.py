import pytest
import asyncio
import base64

from app.objects.c_adversary import Adversary
from app.objects.c_obfuscator import Obfuscator
from app.objects.c_source import Source
from app.objects.secondclass.c_link import Link
from app.objects.secondclass.c_fact import Fact
from app.utility.base_world import BaseWorld

stop_bucket_exhaustion_params = [
    {'stopping_condition_met': False, 'operation_state': 'RUNNING', 'condition_stop': True, 'assert_value': False},
    {'stopping_condition_met': True, 'operation_state': 'RUNNING', 'condition_stop': True, 'assert_value': True},
    {'stopping_condition_met': False, 'operation_state': 'FINISHED', 'condition_stop': True, 'assert_value': True},
    {'stopping_condition_met': True, 'operation_state': 'FINISHED', 'condition_stop': True, 'assert_value': True},
    {'stopping_condition_met': True, 'operation_state': 'RUNNING', 'condition_stop': False, 'assert_value': False}
]

test_string = '#{1_2_3} - #{a.b.c} - #{a.b.d} - #{a.b.e[filters(max=3)]}'
target_string = '#{1_2_3} - 1 - 2 - 3'


class PlannerFake:
    def __init__(self, operation):
        self.state_machine = ['one', 'two', 'three', 'four']
        self.next_bucket = 'one'
        self.stopping_condition_met = False
        self.stopping_conditions = [Fact(trait='j.g.b', value='good')]
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
        self.next_bucket = None

    async def four(self):
        self.calls.append('four')
        self.next_bucket = None


def planner_stub(**kwargs):
    """Creates Planner stub with supplied properties."""
    class PlannerStub:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
    return PlannerStub(**kwargs)


@pytest.fixture
def setup_planning_test(loop, ability, agent, operation, data_svc, init_base_world):
    tability = ability(ability_id='123', executor='sh', platform='darwin', test=BaseWorld.encode_string('mkdir test'),
                       cleanup=BaseWorld.encode_string('rm -rf test'), variations=[], repeatable=True, buckets=['test'])
    tagent = agent(sleep_min=1, sleep_max=2, watchdog=0, executors=['sh'], platform='darwin')
    tsource = Source(id='123', name='test', facts=[], adjustments=[])
    toperation = operation(name='test1', agents=[tagent],
                           adversary=Adversary(name='test', description='test',
                                               atomic_ordering=[],
                                               adversary_id='XYZ'),
                           source=tsource)

    cability = ability(ability_id='321', executor='sh', platform='darwin', test=BaseWorld.encode_string(test_string),
                       cleanup=BaseWorld.encode_string('whoami'), singleton=True, variations=[])

    loop.run_until_complete(data_svc.store(tability))
    loop.run_until_complete(data_svc.store(cability))

    loop.run_until_complete(data_svc.store(
        Obfuscator(name='plain-text',
                   description='Does no obfuscation to any command, instead running it in plain text',
                   module='plugins.stockpile.app.obfuscators.plain_text')
    ))

    yield tability, tagent, toperation, cability


@pytest.fixture(params=stop_bucket_exhaustion_params)
def stop_bucket_exhaustion_setup(request, setup_planning_test):
    """
    Provides setup objects for tests of _stop_bucket_exhaustion().
    """
    _, _, operation, _ = setup_planning_test
    planner = planner_stub(stopping_condition_met=request.param['stopping_condition_met'])
    operation.state = operation.states[request.param["operation_state"]]
    return planner, operation, request.param['condition_stop'], request.param['assert_value']


class TestPlanningService:
    def test_wait_for_links_and_monitor(self, loop, planning_svc, fact,
                                        setup_planning_test):
        # PART A:
        ability, agent, operation, _ = setup_planning_test
        # Add a link to operation.chain
        operation.add_link(Link.load(
            dict(command='', paw=agent.paw, ability=ability, status=0)))
        # Set id to match planner.operation.chain[0].id
        operation.chain[0].id = "123"
        planner = PlannerFake(operation)
        # Create a list containing only the id used above
        link_ids = ["123"]
        # Make sure program doesn't hang in wait_for_links_completion()
        planner.operation.chain[0].finish = True
        assert loop.run_until_complete(planning_svc.wait_for_links_and_monitor(
            planner, operation, link_ids, condition_stop=True)) is False

        # PART B:
        # Make sure program hangs in wait_for_links_completion()
        planner.operation.chain[0].finish = False
        timeout = False
        try:
            loop.run_until_complete(asyncio.wait_for(
                planning_svc.wait_for_links_and_monitor(planner, operation,
                                                        link_ids,
                                                        condition_stop=True),
                timeout=5.0))
        except asyncio.TimeoutError:
            timeout = True
        assert timeout is True

    def test_get_links(self, loop, setup_planning_test, planning_svc, data_svc):
        # PART A: Don't fill in facts for "cability" so only "tability"
        #   is returned in "links"
        tability, agent, operation, cability = setup_planning_test
        operation.adversary.atomic_ordering = ["123", "321"]
        links = loop.run_until_complete(planning_svc.get_links
                                        (operation=operation, buckets=None,
                                         agent=agent))
        assert links[0].ability.ability_id == tability.ability_id

        # PART B: Fill in facts to allow "cability" to be returned in "links"
        #   in addition to "tability"
        operation.add_link(Link.load(
            dict(command='', paw=agent.paw, ability=tability, status=0)))
        operation.chain[0].facts.append(Fact(trait='a.b.c', value='1'))
        operation.chain[0].facts.append(Fact(trait='a.b.d', value='2'))
        operation.chain[0].facts.append(Fact(trait='a.b.e', value='3'))
        links = loop.run_until_complete(planning_svc.get_links
                                        (operation=operation, buckets=None,
                                         agent=agent))

        assert links[0].ability.ability_id == cability.ability_id
        assert links[1].ability.ability_id == tability.ability_id
        assert base64.b64decode(links[0].command).decode('utf-8') == target_string

    def test_exhaust_bucket(self, loop, setup_planning_test, planning_svc):
        ability, agent, operation, _ = setup_planning_test
        operation.adversary.atomic_ordering = ["123"]
        operation.add_link(Link.load(
            dict(command='', paw=agent.paw, ability=ability, status=0)))
        operation.chain[0].finish = True
        planner = PlannerFake(operation)
        bucket = "test"
        timeout = False
        try:
            loop.run_until_complete(asyncio.wait_for(planning_svc.exhaust_bucket(
                planner, bucket, operation, agent), timeout=5.0))
        except asyncio.TimeoutError:
            timeout = True
        assert timeout is True

    def test_add_ability_to_bucket(self, loop, setup_planning_test, planning_svc):
        b1 = 'salvador'
        b2 = 'hardin'
        a, _, _, _ = setup_planning_test
        loop.run_until_complete(planning_svc.add_ability_to_bucket(a, b1))
        assert a.buckets == ['test', b1]
        loop.run_until_complete(planning_svc.add_ability_to_bucket(a, b2))
        assert a.buckets == ['test', b1, b2]

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
        ability, agent, operation, _ = setup_planning_test
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
        ability, agent, operation, _ = setup_planning_test
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
        a, _, _, _ = setup_planning_test
        l1 = link(command='m', paw='1', ability=a, score=1)
        l2 = link(command='a', paw='2', ability=a, score=2)
        l3 = link(command='l', paw='3', ability=a, score=3)
        sl = loop.run_until_complete(planning_svc.sort_links([l2, l1, l3]))
        assert sl[0] == l3
        assert sl[1] == l2
        assert sl[2] == l1

    def test_stop_bucket_exhaustion(self, loop, stop_bucket_exhaustion_setup, planning_svc):
        """
        NOTE: Test runs 5x, each with parameter sets found in 'stop_bucket_exhaustion_params'.
        """
        planner, operation, condition_stop, assert_value = stop_bucket_exhaustion_setup
        assert loop.run_until_complete(planning_svc._stop_bucket_exhaustion(planner, operation, condition_stop)) is assert_value

    def test_execute_planner(self, loop, setup_planning_test, planning_svc, monkeypatch):
        """
        Case 1 - let planner run until it stops itself after bucket 'three'.
        """
        ability, agent, operation, _ = setup_planning_test
        p = PlannerFake(operation)
        loop.run_until_complete(planning_svc.execute_planner(p, publish_transitions=False))
        assert p.calls == ['one', 'two', 'three']

    def test_execute_planner_2(self, monkeypatch, loop, planning_svc, setup_planning_test):
        """
        Case 2 - start planner but then hijack operation after bucket 'two and flag that stopping condition
        been found, thus stopping the planner when it attempt to proceed to next bucket
        """
        ability, agent, operation, _ = setup_planning_test

        async def stub_update_stopping_condition_met(planner, operation):
            if planner.calls == ['one', 'two']:
                planner.stopping_condition_met = True
        monkeypatch.setattr(planning_svc, 'update_stopping_condition_met', stub_update_stopping_condition_met)
        p = PlannerFake(operation)
        loop.run_until_complete(planning_svc.execute_planner(p, publish_transitions=False))
        assert p.calls == ['one', 'two']

    def test_execute_planner_3(self, monkeypatch, loop, planning_svc, setup_planning_test):
        """
        Case 3 - start planner but then hijack operation and set it to 'FINISH' state, thus
        stopping the planner when it attempts to proceed to next bucket
        """
        ability, agent, operation, _ = setup_planning_test

        async def stub_update_stopping_condition_met_1(planner, operation):
            if planner.calls == ['one']:
                operation.state = operation.states['FINISHED']
        monkeypatch.setattr(planning_svc, 'update_stopping_condition_met', stub_update_stopping_condition_met_1)
        p = PlannerFake(operation)
        loop.run_until_complete(planning_svc.execute_planner(p, publish_transitions=False))
        assert p.calls == ['one']

    def test_get_cleanup_links(self, loop, setup_planning_test, planning_svc):
        ability, agent, operation, _ = setup_planning_test
        operation.add_link(Link.load(dict(command='', paw=agent.paw, ability=ability, status=0)))
        links = loop.run_until_complete(
            planning_svc.get_cleanup_links(operation=operation, agent=agent)
        )
        link_list = list(links)
        assert len(link_list) == 1
        assert link_list[0].command == ability.cleanup[0]

    def test_generate_and_trim_links(self, loop, setup_planning_test, planning_svc):
        ability, agent, operation, _ = setup_planning_test
        generated_links = loop.run_until_complete(planning_svc.generate_and_trim_links(agent, operation, [ability]))
        assert 1 == len(generated_links)

    def test_link_fact_coverage(self, loop, setup_planning_test, planning_svc):
        _, agent, operation, ability = setup_planning_test
        link = Link.load(dict(command=BaseWorld.encode_string(test_string), paw=agent.paw, ability=ability, status=0))
        f1 = Fact(trait='a.b.c', value='1')
        f2 = Fact(trait='a.b.d', value='2')
        f3 = Fact(trait='a.b.e', value='3')

        gen = loop.run_until_complete(planning_svc.add_test_variants([link], agent, facts=[f1, f2, f3]))

        assert len(gen) == 2
        assert BaseWorld.decode_bytes(gen[1].display['command']) == target_string

    def test_filter_bs(self, loop, setup_planning_test, planning_svc):
        _, agent, operation, ability = setup_planning_test
        link = Link.load(dict(command=BaseWorld.encode_string(test_string), paw=agent.paw, ability=ability, status=0))
        f1 = Fact(trait='a.b.c', value='1')
        f2 = Fact(trait='a.b.d', value='2')
        f3 = Fact(trait='a.b.e', value='3')
        f4 = Fact(trait='a.b.e', value='4')
        f5 = Fact(trait='a.b.e', value='5')
        f6 = Fact(trait='a.b.e', value='6')

        gen = loop.run_until_complete(planning_svc.add_test_variants([link], agent, facts=[f1, f2, f3, f4, f5, f6]))

        assert len(gen) == 4
        assert BaseWorld.decode_bytes(gen[1].display['command']) == target_string

    def test_duplicate_lateral_filter(self, loop, setup_planning_test, planning_svc, link, fact):
        ability, agent, operation, sability = setup_planning_test

        l0 = link(command='a0', paw='0', ability=ability)
        l1 = link(command='a1', paw='0', ability=sability)
        l2 = link(command='a0', paw='0', ability=ability)
        l3 = link(command='a1', paw='0', ability=sability)

        l0.status = l0.states['SUCCESS']
        l1.status = l1.states['SUCCESS']

        filtered = [x for x in [l0, l1, l2, l3] if x.ability.singleton]
        assert 2 == len(filtered)

        operation.chain = [l0, l1]

        # test historical filtering
        filt = loop.run_until_complete(planning_svc.remove_completed_links(operation, agent, [l2, l3]))
        assert 1 == len(filt)

        # test parallel filtering
        flat_fil = planning_svc._remove_links_of_duplicate_singletons([[l0, l1, l2, l3],
                                                                       [l0, l1, l2, l3],
                                                                       [l0, l1, l2, l3]])
        assert 7 == len(flat_fil)
