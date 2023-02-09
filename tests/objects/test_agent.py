from base64 import b64decode

from app.objects.c_ability import Ability
from app.objects.c_agent import Agent
from app.objects.secondclass.c_executor import Executor
from app.objects.secondclass.c_fact import Fact


class TestAgent:

    def test_task_no_facts(self, event_loop, data_svc, obfuscator, init_base_world):
        executor = Executor(name='psh', platform='windows', command='whoami')
        ability = Ability(ability_id='123', executors=[executor])
        agent = Agent(paw='123', sleep_min=2, sleep_max=8, watchdog=0, executors=['pwsh', 'psh'], platform='windows')
        event_loop.run_until_complete(agent.task([ability], obfuscator='plain-text'))
        assert 1 == len(agent.links)

    def test_task_missing_fact(self, event_loop, obfuscator, init_base_world):
        executor = Executor(name='psh', platform='windows', command='net user #{domain.user.name} /domain')
        ability = Ability(ability_id='123', executors=[executor])
        agent = Agent(paw='123', sleep_min=2, sleep_max=8, watchdog=0, executors=['pwsh', 'psh'], platform='windows')
        event_loop.run_until_complete(agent.task([ability], obfuscator='plain-text'))
        assert 0 == len(agent.links)

    def test_task_with_facts(self, event_loop, obfuscator, init_base_world, knowledge_svc, fire_event_mock):
        executor = Executor(name='psh', platform='windows', command='net user #{domain.user.name} /domain')
        ability = Ability(ability_id='123', executors=[executor])
        agent = Agent(paw='123', sleep_min=2, sleep_max=8, watchdog=0, executors=['pwsh', 'psh'], platform='windows')
        fact = Fact(trait='domain.user.name', value='bob')
        event_loop.run_until_complete(agent.task([ability], 'plain-text', [fact]))
        assert 1 == len(agent.links)

    def test_builtin_fact_replacement(self, event_loop, obfuscator, init_base_world):
        executor = Executor(name='psh', platform='windows',
                            command='echo #{paw} #{server} #{group} #{location} #{exe_name} #{upstream_dest}')
        ability = Ability(ability_id='123', executors=[executor])
        agent = Agent(paw='123', sleep_min=2, sleep_max=8, watchdog=0, executors=['pwsh', 'psh'], platform='windows',
                      group='my_group', server='http://localhost:8888', location='testlocation', exe_name='testexe')
        event_loop.run_until_complete(agent.task([ability], 'plain-text', []))
        assert 1 == len(agent.links)
        link = agent.links[0]
        decoded_command = b64decode(link.command).decode('utf-8')
        want = 'echo 123 http://localhost:8888 my_group testlocation testexe http://localhost:8888'
        assert want == decoded_command

    def test_builtin_fact_replacement_with_upstream_dest(self, event_loop, obfuscator, init_base_world):
        executor = Executor(name='psh', platform='windows',
                            command='echo #{paw} #{server} #{group} #{location} #{exe_name} #{upstream_dest}')
        ability = Ability(ability_id='123', executors=[executor])
        agent = Agent(paw='123', sleep_min=2, sleep_max=8, watchdog=0, executors=['pwsh', 'psh'], platform='windows',
                      group='my_group', server='http://10.10.10.10:8888', location='testlocation', exe_name='testexe',
                      upstream_dest='http://127.0.0.1:12345')
        event_loop.run_until_complete(agent.task([ability], 'plain-text', []))
        assert 1 == len(agent.links)
        link = agent.links[0]
        decoded_command = b64decode(link.command).decode('utf-8')
        want = 'echo 123 http://10.10.10.10:8888 my_group testlocation testexe http://127.0.0.1:12345'
        assert want == decoded_command

    def test_preferred_executor_psh(self, event_loop, ability, executor):
        executor_test = executor(name='test', platform='windows')
        executor_cmd = executor(name='cmd', platform='windows')
        executor_psh = executor(name='psh', platform='windows')
        test_ability = ability(ability_id='123', executors=[executor_test, executor_cmd, executor_psh])

        agent = Agent(paw='123', sleep_min=2, sleep_max=8, watchdog=0, executors=['psh', 'cmd'], platform='windows')

        preferred_executor = event_loop.run_until_complete(agent.get_preferred_executor(test_ability))
        assert preferred_executor is executor_psh  # 'psh' preferred if available

    def test_preferred_executor_from_agent_executor(self, event_loop, ability, executor):
        executor_test = executor(name='test', platform='windows')
        executor_cmd = executor(name='cmd', platform='windows')
        executor_psh = executor(name='psh', platform='windows')
        test_ability = ability(ability_id='123', executors=[executor_test, executor_cmd, executor_psh])

        agent = Agent(paw='123', sleep_min=2, sleep_max=8, watchdog=0, executors=['cmd', 'test'], platform='windows')

        preferred_executor = event_loop.run_until_complete(agent.get_preferred_executor(test_ability))
        assert preferred_executor is executor_cmd  # prefer agent's first executor, not ability's

    def test_set_pending_executor_path_update(self):
        original_executors = ['cmd', 'test']
        agent = Agent(paw='123', sleep_min=2, sleep_max=8, watchdog=0, executors=original_executors, platform='windows')
        executor_to_change = 'test'
        new_path = 'new_path'
        want = dict(action='update_path', executor=executor_to_change, value=new_path)
        assert agent.executor_change_to_assign is None
        agent.set_pending_executor_path_update(executor_to_change, new_path)
        assert agent.executor_change_to_assign == want
        assert agent.executors == original_executors

    def test_assign_executor_change(self):
        agent = Agent(paw='123', sleep_min=2, sleep_max=8, watchdog=0, executors=['cmd', 'test'], platform='windows')
        executor_to_change = 'test'
        new_path = 'new_path'
        want = dict(action='update_path', executor=executor_to_change, value=new_path)
        agent.set_pending_executor_path_update(executor_to_change, new_path)
        assert agent.assign_pending_executor_change() == want
        assert agent.executor_change_to_assign is None

    def test_set_pending_executor_removal(self):
        agent = Agent(paw='123', sleep_min=2, sleep_max=8, watchdog=0, executors=['cmd', 'test'], platform='windows')
        executor_to_remove = 'test'
        want = dict(executor=executor_to_remove, action='remove')
        agent.set_pending_executor_removal(executor_to_remove)
        assert agent.executor_change_to_assign == want
        assert agent.executors == ['cmd']

    def test_removing_nonexistent_executor(self):
        original_executors = ['cmd', 'test']
        agent = Agent(paw='123', sleep_min=2, sleep_max=8, watchdog=0, executors=original_executors, platform='windows')
        agent.set_pending_executor_removal('idontexist')
        assert agent.executor_change_to_assign is None
        assert agent.executors == original_executors

    def test_updating_nonexistent_executor(self):
        agent = Agent(paw='123', sleep_min=2, sleep_max=8, watchdog=0, executors=['cmd', 'test'], platform='windows')
        agent.set_pending_executor_path_update('idontexist', 'fakepath')
        assert agent.executor_change_to_assign is None

    def test_heartbeat_modification_during_pending_executor_removal(self, event_loop):
        original_executors = ['cmd', 'test']
        agent = Agent(paw='123', sleep_min=2, sleep_max=8, watchdog=0, executors=original_executors, platform='windows')
        agent.set_pending_executor_removal('test')
        event_loop.run_until_complete(agent.heartbeat_modification(executors=original_executors))
        assert agent.executors == ['cmd']

    def test_store_new_agent(self, data_svc):
        agent = Agent(paw='123', sleep_min=2, sleep_max=8, watchdog=0, executors=['cmd', 'test'], platform='windows')
        stored_agent = agent.store(data_svc.ram)
        assert len(data_svc.ram['agents']) == 1
        assert agent in data_svc.ram['agents']
        assert stored_agent == agent

    def test_store_existing_agent(self, data_svc):
        agent = Agent(paw='123', sleep_min=2, group='red', sleep_max=8, watchdog=0, executors=['cmd', 'test'],
                      platform='windows', trusted=True, pending_contact='HTML')
        agent.store(data_svc.ram)
        assert len(data_svc.ram['agents']) == 1
        agent.group = "blue"
        agent.trusted = False
        agent.sleep_min = 1
        agent.sleep_max = 5
        agent.watchdog = 1
        agent.pending_contact = "HTTP"
        stored_agent = agent.store(data_svc.ram)
        assert len(data_svc.ram['agents']) == 1
        assert stored_agent.schema.dump(stored_agent) == agent.schema.dump(agent)
