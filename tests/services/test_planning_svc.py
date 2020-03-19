import pytest

from app.objects.secondclass.c_link import Link
from app.utility.base_world import BaseWorld


@pytest.fixture
def setup_planning_test(loop, ability, agent, operation, data_svc):
    tability = ability(ability_id='123', executor='sh', test=BaseWorld.encode_string('mkdir test'),
                       cleanup=BaseWorld.encode_string('rm -rf test'), variations=[])
    tagent = agent(sleep_min=1, sleep_max=2, watchdog=0)
    toperation = operation(name='test1', agents=tagent, adversary='hunter')
    loop.run_until_complete(data_svc.store(tability))
    yield (tability, tagent, toperation)


class TestPlanningService:

    def test_get_cleanup_links(self, loop, setup_planning_test, planning_svc):
        ability, agent, operation = setup_planning_test
        operation.add_link(Link(operation=operation, command='', paw=agent.paw, ability=ability, status=0))
        links = loop.run_until_complete(
            planning_svc.get_cleanup_links(operation=operation, agent=agent)
        )
        link_list = list(links)
        assert len(link_list) == 1
        assert link_list[0].command == ability.cleanup[0]
