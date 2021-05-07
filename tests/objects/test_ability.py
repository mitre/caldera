from app.objects.c_ability import Ability
from app.objects.c_agent import Agent


class TestAbility:

    def test_privileged_to_run__1(self, loop, data_svc):
        """ Test ability.privilege == None """
        agent = loop.run_until_complete(data_svc.store(Agent(sleep_min=1, sleep_max=2, watchdog=0)))
        ability = loop.run_until_complete(data_svc.store(
            Ability(ability_id='123', privilege=None)
        ))
        assert agent.privileged_to_run(ability)

    def test_privileged_to_run__2(self, loop, data_svc):
        """ Test ability.privilege == 'User' """
        agent = loop.run_until_complete(data_svc.store(Agent(sleep_min=1, sleep_max=2, watchdog=0)))
        ability = loop.run_until_complete(data_svc.store(
            Ability(ability_id='123', privilege='User')
        ))
        assert agent.privileged_to_run(ability)

    def test_privileged_to_run__3(self, loop, data_svc):
        """ Test ability.privilege == 'Elevated' """
        agent = loop.run_until_complete(data_svc.store(Agent(sleep_min=1, sleep_max=2, watchdog=0)))
        ability = loop.run_until_complete(data_svc.store(
            Ability(ability_id='123', privilege='Elevated')
        ))
        assert not agent.privileged_to_run(ability)

    def test_privileged_to_run__4(self, loop, data_svc):
        """ Test ability.privilege == 'User' and agent.privilege == 'Elevated' """
        agent = loop.run_until_complete(data_svc.store(Agent(sleep_min=1, sleep_max=2, watchdog=0, privilege='Elevated')))
        ability = loop.run_until_complete(data_svc.store(
            Ability(ability_id='123', privilege='User')
        ))
        assert agent.privileged_to_run(ability)

    def test_privileged_to_run__5(self, loop, data_svc):
        """ Test ability.privilege == 'Elevated' and agent.privilege == 'Elevated' """
        agent = loop.run_until_complete(data_svc.store(Agent(sleep_min=1, sleep_max=2, watchdog=0, privilege='Elevated')))
        ability = loop.run_until_complete(data_svc.store(
            Ability(ability_id='123', privilege='Elevated')
        ))
        assert agent.privileged_to_run(ability)

    def test_privileged_to_run__6(self, loop, data_svc):
        """ Test ability.privilege == 'None' and agent.privilege == 'Elevated' """
        agent = loop.run_until_complete(data_svc.store(Agent(sleep_min=1, sleep_max=2, watchdog=0, privilege='Elevated')))
        ability = loop.run_until_complete(data_svc.store(
            Ability(ability_id='123')
        ))
        assert agent.privileged_to_run(ability)

    def test_executor_storage(self, loop, ability, executor):
        test_executor = executor()
        test_ability = ability(executors=[test_executor])

        assert len(list(test_ability.executors)) == 1

    def test_executor_search(self, loop, ability, executor):
        test_executor = executor(name='psh', platform='windows')
        test_ability = ability(executors=[test_executor])

        found_executor = test_ability.find_executor(name='psh', platform='windows')
        assert found_executor is test_executor

    def test_executor_search_duplicate(self, loop, ability, executor):
        test_executor = executor(name='psh', platform='windows')
        test_ability = ability(executors=[test_executor])

        found_executors = test_ability.find_executors(names=['psh', 'psh'], platform='windows')
        assert len(found_executors) == 1
        assert found_executors[0] is test_executor

    def test_executor_overwrite(self, loop, ability, executor):
        test_executor_1 = executor()
        test_executor_2 = executor()
        test_ability = ability(executors=[test_executor_1, test_executor_2])

        assert len(list(test_ability.executors)) == 1
        assert next(test_ability.executors) is test_executor_2

    def test_executor_removal(self, loop, ability, executor):
        test_ability = ability(executors=[executor()])
        test_ability.remove_all_executors()

        assert len(list(test_ability.executors)) == 0
