from app.objects.c_ability import Ability
from app.objects.c_agent import Agent
from tests.base.test_base import TestBase


class TestAbility(TestBase):

    def setUp(self):
        self.initialize()

    def test_privileged_to_run__1(self):
        """ Test ability.privilege == None """
        agent = self.run_async(self.data_svc.store(Agent(sleep_min=1, sleep_max=2, watchdog=0)))
        ability = self.run_async(self.data_svc.store(
            Ability(ability_id='123', privilege=None, variations=[])
        ))
        self.assertTrue(agent.privileged_to_run(ability))

    def test_privileged_to_run__2(self):
        """ Test ability.privilege == 'User' """
        agent = self.run_async(self.data_svc.store(Agent(sleep_min=1, sleep_max=2, watchdog=0)))
        ability = self.run_async(self.data_svc.store(
            Ability(ability_id='123', privilege='User', variations=[])
        ))
        self.assertTrue(agent.privileged_to_run(ability))

    def test_privileged_to_run__3(self):
        """ Test ability.privilege == 'Elevated' """
        agent = self.run_async(self.data_svc.store(Agent(sleep_min=1, sleep_max=2, watchdog=0)))
        ability = self.run_async(self.data_svc.store(
            Ability(ability_id='123', privilege='Elevated', variations=[])
        ))
        self.assertFalse(agent.privileged_to_run(ability))

    def test_privileged_to_run__4(self):
        """ Test ability.privilege == 'User' and agent.privilege == 'Elevated' """
        agent = self.run_async(self.data_svc.store(Agent(sleep_min=1, sleep_max=2, watchdog=0, privilege='Elevated')))
        ability = self.run_async(self.data_svc.store(
            Ability(ability_id='123', privilege='User', variations=[])
        ))
        self.assertTrue(agent.privileged_to_run(ability))

    def test_privileged_to_run__5(self):
        """ Test ability.privilege == 'Elevated' and agent.privilege == 'Elevated' """
        agent = self.run_async(self.data_svc.store(Agent(sleep_min=1, sleep_max=2, watchdog=0, privilege='Elevated')))
        ability = self.run_async(self.data_svc.store(
            Ability(ability_id='123', privilege='Elevated', variations=[])
        ))
        self.assertTrue(agent.privileged_to_run(ability))

    def test_privileged_to_run__6(self):
        """ Test ability.privilege == 'None' and agent.privilege == 'Elevated' """
        agent = self.run_async(self.data_svc.store(Agent(sleep_min=1, sleep_max=2, watchdog=0, privilege='Elevated')))
        ability = self.run_async(self.data_svc.store(
            Ability(ability_id='123', variations=[])
        ))
        self.assertTrue(agent.privileged_to_run(ability))
