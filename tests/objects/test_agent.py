from app.objects.c_ability import Ability
from app.objects.c_agent import Agent
from app.objects.secondclass.c_fact import Fact
from app.utility.base_world import BaseWorld


class TestAgent:

    def test_task_no_facts(self, loop, data_svc, obfuscator, init_base_world):
        ability = Ability(ability_id='123', test=BaseWorld.encode_string('whoami'), variations=[],
                          executor='psh', platform='windows')
        agent = Agent(paw='123', sleep_min=2, sleep_max=8, watchdog=0, executors=['pwsh', 'psh'], platform='windows')
        loop.run_until_complete(agent.task([ability], obfuscator='plain-text'))
        assert 1 == len(agent.links)

    def test_task_missing_fact(self, loop, obfuscator, init_base_world):
        ability = Ability(ability_id='123', test=BaseWorld.encode_string('net user #{domain.user.name} /domain'),
                          variations=[], executor='psh', platform='windows')
        agent = Agent(paw='123', sleep_min=2, sleep_max=8, watchdog=0, executors=['pwsh', 'psh'], platform='windows')
        loop.run_until_complete(agent.task([ability], obfuscator='plain-text'))
        assert 0 == len(agent.links)

    def test_task_with_facts(self, loop, obfuscator, init_base_world):
        ability = Ability(ability_id='123', test=BaseWorld.encode_string('net user #{domain.user.name} /domain'),
                          variations=[], executor='psh', platform='windows')
        agent = Agent(paw='123', sleep_min=2, sleep_max=8, watchdog=0, executors=['pwsh', 'psh'], platform='windows')
        fact = Fact(trait='domain.user.name', value='bob')

        loop.run_until_complete(agent.task([ability], 'plain-text', [fact]))
        assert 1 == len(agent.links)
