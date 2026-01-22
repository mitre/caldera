import pytest

from base64 import b64encode, b64decode
from app.utility.base_service import BaseService
from app.objects.c_agent import Agent
from app.objects.secondclass.c_link import Link
from app.objects.c_ability import Ability, AbilitySchema
from app.objects.secondclass.c_executor import Executor, ExecutorSchema
from app.obfuscators.base64_basic import Obfuscation


@pytest.fixture
def b64basic_obfuscator():
    def _generate_obfuscator(obfuscator_agent):
        return Obfuscation(obfuscator_agent)

    return _generate_obfuscator


@pytest.fixture
def test_windows_agent(event_loop):
    agent = Agent(paw='123', sleep_min=2, sleep_max=8, watchdog=0, executors=['psh'], platform='windows')
    event_loop.run_until_complete(BaseService.get_service('data_svc').store(agent))
    return agent


@pytest.fixture
def test_windows_executor(test_windows_agent):
    return ExecutorSchema().load(dict(timeout=60, platform=test_windows_agent.platform, name='psh', command='ls'))


@pytest.fixture
def test_windows_ability(test_windows_executor, event_loop):
    ability = AbilitySchema().load(dict(ability_id='123',
                                        tactic='discovery',
                                        technique_id='auto-generated',
                                        technique_name='auto-generated',
                                        name='Manual Command',
                                        description='test windows ability',
                                        executors=[ExecutorSchema().dump(test_windows_executor)]))
    event_loop.run_until_complete(BaseService.get_service('data_svc').store(ability))
    return ability


@pytest.fixture
def finished_windows_link(test_windows_executor, test_windows_agent, test_windows_ability):
    return {
        'command': str(b64encode(test_windows_executor.command.encode()), 'utf-8'),
        'paw': test_windows_agent.paw,
        'ability': test_windows_ability,
        'executor': test_windows_executor,
        'host': test_windows_agent.host,
        'deadman': False,
        'used': [],
        'id': '789',
        'relationships': [],
        'status': 0,
        'output': 'test_dir'
    }

class TestBase64BasicObfuscator:
    def test_b64basic_obfuscator(self, b64basic_obfuscator, test_agent, test_windows_agent, finished_link, finished_windows_link):
        # sh
        linux_obfuscator = b64basic_obfuscator(test_agent)
        sh_link = Link.load(finished_link)
        expected_encoded = 'eval "$(echo bHM= | base64 --decode)"'
        decoded = linux_obfuscator.run(sh_link)
        assert decoded == expected_encoded

        # psh
        windows_obfuscator = b64basic_obfuscator(test_windows_agent)
        psh_link = Link.load(finished_windows_link)
        expected_encoded = 'powershell -Enc bABzAA=='
        decoded = windows_obfuscator.run(psh_link)
        assert decoded == expected_encoded
        

