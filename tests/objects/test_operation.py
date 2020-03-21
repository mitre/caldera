import pytest

from app.objects.c_adversary import Adversary
from app.utility.base_world import BaseWorld


@pytest.fixture
def setup_operation_test(operation):
    BaseWorld.apply_config('abilities', BaseWorld.strip_yml('conf/abilities.yml')[0])


@pytest.mark.usefixtures(
    'setup_operation_test'
)
class TestOperation:

    @pytest.fixture
    def demo_operation(self, loop, data_svc, operation):
        adversary = loop.run_until_complete(data_svc.store(
            Adversary(adversary_id='123', name='test', description='test adversary', phases=dict())
        ))
        toperation = operation(name='my first op', agents=[], adversary=adversary)
        yield toperation

    def test__get_unique_payload_key_no_real_payloads(self, loop, demo_operation):
        payloads = BaseWorld.get_config(prop='obfuscated_payloads', name='abilities').get('names')
        payload_name = demo_operation._get_unique_payload_key(payload_name_len=10)
        assert payload_name in payloads

    def test__get_unique_payload_key_force_random(self, loop, demo_operation):
        payloads = BaseWorld.get_config(prop='obfuscated_payloads', name='abilities').get('names')
        for name in payloads:
            demo_operation.payloads_map['to_real_payload'][name] = ''
        payload_name = demo_operation._get_unique_payload_key(payload_name_len=10)
        assert payload_name not in payloads
        assert len(payload_name) == 10
