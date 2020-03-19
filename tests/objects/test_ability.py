from app.objects.c_ability import Ability
from app.objects.c_agent import Agent


class TestAbility:

    def test_privileged_to_run__1(self, loop, data_svc):
        """ Test ability.privilege == None """
        agent = loop.run_until_complete(data_svc.store(Agent(sleep_min=1, sleep_max=2, watchdog=0)))
        ability = loop.run_until_complete(data_svc.store(
            Ability(ability_id='123', privilege=None, variations=[])
        ))
        assert agent.privileged_to_run(ability)

    def test_privileged_to_run__2(self, loop, data_svc):
        """ Test ability.privilege == 'User' """
        agent = loop.run_until_complete(data_svc.store(Agent(sleep_min=1, sleep_max=2, watchdog=0)))
        ability = loop.run_until_complete(data_svc.store(
            Ability(ability_id='123', privilege='User', variations=[])
        ))
        assert agent.privileged_to_run(ability)

    def test_privileged_to_run__3(self, loop, data_svc):
        """ Test ability.privilege == 'Elevated' """
        agent = loop.run_until_complete(data_svc.store(Agent(sleep_min=1, sleep_max=2, watchdog=0)))
        ability = loop.run_until_complete(data_svc.store(
            Ability(ability_id='123', privilege='Elevated', variations=[])
        ))
        assert not agent.privileged_to_run(ability)

    def test_privileged_to_run__4(self, loop, data_svc):
        """ Test ability.privilege == 'User' and agent.privilege == 'Elevated' """
        agent = loop.run_until_complete(data_svc.store(Agent(sleep_min=1, sleep_max=2, watchdog=0, privilege='Elevated')))
        ability = loop.run_until_complete(data_svc.store(
            Ability(ability_id='123', privilege='User', variations=[])
        ))
        assert agent.privileged_to_run(ability)

    def test_privileged_to_run__5(self, loop, data_svc):
        """ Test ability.privilege == 'Elevated' and agent.privilege == 'Elevated' """
        agent = loop.run_until_complete(data_svc.store(Agent(sleep_min=1, sleep_max=2, watchdog=0, privilege='Elevated')))
        ability = loop.run_until_complete(data_svc.store(
            Ability(ability_id='123', privilege='Elevated', variations=[])
        ))
        assert agent.privileged_to_run(ability)

    def test_privileged_to_run__6(self, loop, data_svc):
        """ Test ability.privilege == 'None' and agent.privilege == 'Elevated' """
        agent = loop.run_until_complete(data_svc.store(Agent(sleep_min=1, sleep_max=2, watchdog=0, privilege='Elevated')))
        ability = loop.run_until_complete(data_svc.store(
            Ability(ability_id='123', variations=[])
        ))
        assert agent.privileged_to_run(ability)
