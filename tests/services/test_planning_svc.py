import pytest

from app.objects.secondclass.c_link import Link
from app.utility.base_world import BaseWorld


@pytest.mark.usefixtures(
    'init_base_world'
)
class TestPlanningService:

    @pytest.fixture
    def agent_op_pair(self, operation, agent):
        tagent = agent(sleep_min=1, sleep_max=2, watchdog=0)
        toperation = operation(name='test1', agents=tagent, adversary='hunter')
        yield (tagent, toperation)

    def test_get_cleanup_links(self, loop, agent_op_pair, ability, data_svc, planning_svc):
        agent, operation = agent_op_pair
        tability = ability(ability_id='123', executor='sh', test=BaseWorld.encode_string('mkdir test'),
                           cleanup=BaseWorld.encode_string('rm -rf test'), variations=[])
        loop.run_until_complete(data_svc.store(tability))

        operation.add_link(Link(operation=operation, command='', paw=agent.paw, ability=tability, status=0))
        links = loop.run_until_complete(
            planning_svc.get_cleanup_links(operation=operation, agent=agent)
        )
        link_list = list(links)
        assert len(link_list) == 1
        assert link_list[0].command == tability.cleanup[0]

    def test_get_cleanup_links_obfuscated_payloads(self, loop, agent_op_pair, ability, data_svc, planning_svc):
        # test cleaning up links with obfuscated payloads enabled
        agent, operation = agent_op_pair
        operation.obfuscate_payloads = True
        orig_payload_name = 'plnsvc_obfuscated_payload'

        tability = ability(ability_id='123', executor='sh', payload=orig_payload_name, test=BaseWorld.encode_string('mkdir test'),
                           cleanup=BaseWorld.encode_string('%s -rf test' % orig_payload_name), variations=[])
        loop.run_until_complete(data_svc.store(tability))

        operation.add_link(Link(operation=operation, command='', paw=agent.paw, ability=tability, status=0))
        links = loop.run_until_complete(
            planning_svc.get_cleanup_links(operation=operation, agent=agent)
        )
        link_list = list(links)
        assert len(link_list) == 1
        # ensure the original payload name is not in the command of the link
        assert orig_payload_name not in link_list[0].command
