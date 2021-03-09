import pytest

from base64 import b64encode
from datetime import datetime
from unittest.mock import MagicMock

from app.objects.c_operation import Operation
from app.objects.secondclass.c_link import Link


@pytest.fixture
def operation_agent(agent):
    return agent(sleep_min=30, sleep_max=60, watchdog=0, platform='windows', host='WORKSTATION',
                 username='testagent', architecture='amd64', group='red', location='C:\\Users\\Public\\test.exe',
                 pid=1234, ppid=123, executors=['psh'], privilege='User', exe_name='test.exe', contact='unknown',
                 paw='testpaw')


@pytest.fixture
def operation_adversary(adversary):
    return adversary(adversary_id='123', name='test adversary', description='test adversary desc')


@pytest.fixture
def operation_link():
    def _generate_link(command, paw, ability, pid=0, decide=None, collect=None, finish=None, **kwargs):
        generated_link = Link(command, paw, ability, **kwargs)
        generated_link.pid = pid
        if decide:
            generated_link.decide = decide
        if collect:
            generated_link.collect = collect
        if finish:
            generated_link.finish = finish
        return generated_link
    return _generate_link


@pytest.fixture
def encoded_command():
    def _encode_command(command_str):
        return b64encode(command_str.encode('utf-8')).decode()
    return _encode_command


@pytest.fixture
def op_for_event_logs(operation_agent, operation_adversary, ability, operation_link, encoded_command):
    op = Operation(name='test', agents=[operation_agent], adversary=operation_adversary)
    op.set_start_details()
    encoded_command_1 = encoded_command('whoami')
    encoded_command_2 = encoded_command('hostname')
    ability_1 = ability(ability_id='123', tactic='test tactic', technique_id='T0000', technique='test technique',
                        name='test ability', description='test ability desc', executor='psh', platform='windows',
                        test=encoded_command_1)
    ability_2 = ability(ability_id='456', tactic='test tactic', technique_id='T0000', technique='test technique',
                        name='test ability 2', description='test ability 2 desc', executor='psh',
                        platform='windows', test=encoded_command_2)
    link_1 = operation_link(ability=ability_1, paw=operation_agent.paw,
                            command=encoded_command_1, status=0, host=operation_agent.host, pid=789,
                            decide=datetime.strptime('2021-01-01 08:00:00', '%Y-%m-%d %H:%M:%S'),
                            collect=datetime.strptime('2021-01-01 08:01:00', '%Y-%m-%d %H:%M:%S'),
                            finish='2021-01-01 08:02:00')
    link_2 = operation_link(ability=ability_2, paw=operation_agent.paw,
                            command=encoded_command_2, status=0, host=operation_agent.host, pid=7890,
                            decide=datetime.strptime('2021-01-01 09:00:00', '%Y-%m-%d %H:%M:%S'),
                            collect=datetime.strptime('2021-01-01 09:01:00', '%Y-%m-%d %H:%M:%S'),
                            finish='2021-01-01 09:02:00')
    discarded_link = operation_link(ability=ability_2, paw=operation_agent.paw,
                                    command=encoded_command_2, status=-2, host=operation_agent.host, pid=7891,
                                    decide=datetime.strptime('2021-01-01 10:00:00', '%Y-%m-%d %H:%M:%S'))
    op.chain = [link_1, link_2, discarded_link]
    return op


class TestOperation:
    def test_ran_ability_id(self, ability, adversary):
        op = Operation(name='test', agents=[], adversary=adversary)
        mock_link = MagicMock(spec=Link, ability=ability(ability_id='123'), finish='2021-01-01 08:00:00')
        op.chain = [mock_link]
        assert op.ran_ability_id('123')

    def test_event_logs(self, loop, op_for_event_logs, operation_agent, file_svc, data_svc):
        loop.run_until_complete(data_svc.store(operation_agent))
        start_time = op_for_event_logs.start.strftime('%Y-%m-%d %H:%M:%S')
        agent_creation_time = operation_agent.created.strftime('%Y-%m-%d %H:%M:%S')
        want_agent_metadata = dict(
            paw='testpaw',
            group='red',
            architecture='amd64',
            username='testagent',
            location='C:\\Users\\Public\\test.exe',
            pid=1234,
            ppid=123,
            privilege='User',
            host='WORKSTATION',
            contact='unknown',
            created=agent_creation_time,
        )
        want_operation_metadata = dict(
            operation_name='test',
            operation_start=start_time,
            operation_adversary='test adversary',
        )
        want_attack_metadata = dict(
            tactic='test tactic',
            technique_name='test technique',
            technique_id='T0000',
        )
        want = [
            dict(
                command='d2hvYW1p',
                delegated_timestamp='2021-01-01 08:00:00',
                collected_timestamp='2021-01-01 08:01:00',
                finished_timestamp='2021-01-01 08:02:00',
                status=0,
                platform='windows',
                executor='psh',
                pid=789,
                agent_metadata=want_agent_metadata,
                ability_metadata=dict(
                  ability_id='123',
                  ability_name='test ability',
                  ability_description='test ability desc',
                ),
                operation_metadata=want_operation_metadata,
                attack_metadata=want_attack_metadata,
            ),
            dict(
                command='aG9zdG5hbWU=',
                delegated_timestamp='2021-01-01 09:00:00',
                collected_timestamp='2021-01-01 09:01:00',
                finished_timestamp='2021-01-01 09:02:00',
                status=0,
                platform='windows',
                executor='psh',
                pid=7890,
                agent_metadata=want_agent_metadata,
                ability_metadata=dict(
                    ability_id='456',
                    ability_name='test ability 2',
                    ability_description='test ability 2 desc',
                ),
                operation_metadata=want_operation_metadata,
                attack_metadata=want_attack_metadata,
            ),
        ]
        event_logs = loop.run_until_complete(op_for_event_logs.event_logs(file_svc, data_svc))
        assert event_logs == want
