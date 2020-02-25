from app.objects.c_ability import Ability
from app.objects.c_agent import Agent
from app.objects.c_operation import Operation
from app.objects.secondclass.c_link import Link
from app.utility.base_world import BaseWorld
from tests.base.test_base import TestBase


class TestPlanningService(TestBase):

    def setUp(self):
        self.initialize()
        self.ability = Ability(ability_id='123', executor='sh', test=BaseWorld.encode_string('mkdir test'), cleanup=BaseWorld.encode_string('rm -rf test'))
        self.agent = Agent(sleep_min=1, sleep_max=2, watchdog=0)
        self.operation = Operation(name='test1', agents=self.agent, adversary='hunter')
        self.run_async(self.data_svc.store(self.ability))

    def test_get_cleanup_links(self):
        self.operation.add_link(Link(operation=self.operation, command='', paw=self.agent.paw, ability=self.ability, status=0))
        links = self.run_async(
            self.planning_svc.get_cleanup_links(operation=self.operation, agent=self.agent)
        )
        link_list = list(links)
        self.assertEqual(len(link_list), 1)
        self.assertEqual(link_list[0].command, self.ability.cleanup)
