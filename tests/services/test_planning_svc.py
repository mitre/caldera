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
