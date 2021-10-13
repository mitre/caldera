import base64
import json
import os
from base64 import b64encode
from datetime import datetime
from unittest import mock
from unittest.mock import MagicMock

import pytest

from app.objects.c_operation import Operation
from app.objects.secondclass.c_link import Link
from app.service.interfaces.i_event_svc import EventServiceInterface
from app.utility.base_service import BaseService
from app.objects.c_source import Source
from app.objects.c_planner import Planner
from app.objects.c_objective import Objective
from app.objects.secondclass.c_result import Result
from app.objects.secondclass.c_fact import Fact

TIME_FORMAT = '%Y-%m-%d %H:%M:%S'


@pytest.fixture
def operation_agent(agent):
    return agent(sleep_min=30, sleep_max=60, watchdog=0, platform='windows', host='WORKSTATION',
                 username='testagent', architecture='amd64', group='red', location=r'C:\Users\Public\test.exe',
                 pid=1234, ppid=123, executors=['psh'], privilege='User', exe_name='test.exe', contact='unknown',
                 paw='testpaw')


@pytest.fixture
def operation_adversary(adversary):
    return adversary(adversary_id='123', name='test adversary', description='test adversary desc')


@pytest.fixture
def operation_link():
    def _generate_link(command, paw, ability, executor, pid=0, decide=None, collect=None, finish=None, **kwargs):
        generated_link = Link(command, paw, ability, executor, **kwargs)
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
def op_for_event_logs(operation_agent, operation_adversary, executor, ability, operation_link, encoded_command):
    op = Operation(name='test', agents=[operation_agent], adversary=operation_adversary)
    op.set_start_details()
    command_1 = 'whoami'
    command_2 = 'hostname'
    executor_1 = executor(name='psh', platform='windows', command=command_1)
    executor_2 = executor(name='psh', platform='windows', command=command_2)
    ability_1 = ability(ability_id='123', tactic='test tactic', technique_id='T0000', technique_name='test technique',
                        name='test ability', description='test ability desc', executors=[executor_1])
    ability_2 = ability(ability_id='456', tactic='test tactic', technique_id='T0000', technique_name='test technique',
                        name='test ability 2', description='test ability 2 desc', executors=[executor_2])
    link_1 = operation_link(ability=ability_1, paw=operation_agent.paw, executor=executor_1,
                            command=encoded_command(command_1), status=0, host=operation_agent.host, pid=789,
                            decide=datetime.strptime('2021-01-01 08:00:00', TIME_FORMAT),
                            collect=datetime.strptime('2021-01-01 08:01:00', TIME_FORMAT),
                            finish='2021-01-01 08:02:00')
    link_2 = operation_link(ability=ability_2, paw=operation_agent.paw, executor=executor_2,
                            command=encoded_command(command_2), status=0, host=operation_agent.host, pid=7890,
                            decide=datetime.strptime('2021-01-01 09:00:00', TIME_FORMAT),
                            collect=datetime.strptime('2021-01-01 09:01:00', TIME_FORMAT),
                            finish='2021-01-01 09:02:00')
    discarded_link = operation_link(ability=ability_2, paw=operation_agent.paw, executor=executor_2,
                                    command=encoded_command(command_2), status=-2, host=operation_agent.host, pid=7891,
                                    decide=datetime.strptime('2021-01-01 10:00:00', TIME_FORMAT))
    op.chain = [link_1, link_2, discarded_link]
    return op


@pytest.fixture
def fake_event_svc(loop):
    class FakeEventService(BaseService, EventServiceInterface):
        def __init__(self):
            self.fired = {}

        def reset(self):
            self.fired = {}

        async def observe_event(self, callback, exchange=None, queue=None):
            pass

        async def fire_event(self, exchange=None, queue=None, timestamp=True, **callback_kwargs):
            self.fired[exchange, queue] = callback_kwargs

    service = FakeEventService()
    service.add_service('event_svc', service)

    yield service

    BaseService.remove_service('event_svc')


@pytest.fixture
def test_ability(ability, executor):
    return ability(ability_id='123', executors=[executor(name='psh', platform='windows')])


@pytest.fixture
def make_test_link(test_ability):
    def _make_link(link_id):
        return Link(command='', paw='123456', ability=test_ability, id=link_id, executor=next(test_ability.executors))
    return _make_link


@pytest.fixture
def make_test_result():
    def _make_result(link_id):
        result = dict(
            id=link_id,
            output=str(base64.b64encode('10.10.10.10'.encode('utf-8')).decode('utf-8')),
            pid=0,
            status=0
        )
        return Result(**result)
    return _make_result


@pytest.fixture
def op_with_learning_parser(ability, adversary):
    op = Operation(id='12345', name='testA', agents=[], adversary=adversary, use_learning_parsers=True)
    return op


@pytest.fixture
def op_without_learning_parser(ability, adversary):
    op = Operation(id='54321', name='testB', agents=[], adversary=adversary, use_learning_parsers=False)
    return op


@pytest.fixture
def op_with_learning_and_seeded(ability, adversary, operation_agent):
    sc = Source(id='3124', name='test', facts=[Fact(trait='domain.user.name', value='bob')])
    op = Operation(id='6789', name='testC', agents=[], adversary=adversary, source=sc, use_learning_parsers=True)
    # patch operation to make it 'realistic'
    op.start = datetime.strptime('2021-01-01 09:00:00', TIME_FORMAT)
    op.adversary = op.adversary()
    op.planner = Planner(planner_id='12345', name='test_planner',
                                                  module='not.an.actual.planner', params=None)
    op.objective = Objective(id='6428', name='not_an_objective')
    t_operation_agent = operation_agent
    t_operation_agent.paw = '123456'
    op.agents = [t_operation_agent]
    return op


class TestOperation:
    def test_ran_ability_id(self, ability, adversary):
        op = Operation(name='test', agents=[], adversary=adversary)
        mock_link = MagicMock(spec=Link, ability=ability(ability_id='123'), finish='2021-01-01 08:00:00')
        op.chain = [mock_link]
        assert op.ran_ability_id('123')

    def test_event_logs(self, loop, op_for_event_logs, operation_agent, file_svc, data_svc):
        loop.run_until_complete(data_svc.remove('agents', match=dict(unique=operation_agent.unique)))
        loop.run_until_complete(data_svc.store(operation_agent))
        start_time = op_for_event_logs.start.strftime(TIME_FORMAT)
        agent_creation_time = operation_agent.created.strftime(TIME_FORMAT)
        want_agent_metadata = dict(
            paw='testpaw',
            group='red',
            architecture='amd64',
            username='testagent',
            location=r'C:\Users\Public\test.exe',
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

    def test_writing_event_logs_to_disk(self, loop, op_for_event_logs, operation_agent, file_svc, data_svc):
        loop.run_until_complete(data_svc.remove('agents', match=dict(unique=operation_agent.unique)))
        loop.run_until_complete(data_svc.store(operation_agent))

        start_time = op_for_event_logs.start.strftime(TIME_FORMAT)
        agent_creation_time = operation_agent.created.strftime(TIME_FORMAT)
        want_agent_metadata = dict(
            paw='testpaw',
            group='red',
            architecture='amd64',
            username='testagent',
            location=r'C:\Users\Public\test.exe',
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
        loop.run_until_complete(op_for_event_logs.write_event_logs_to_disk(file_svc, data_svc))
        target_path = '/tmp/event_logs/operation_%s.json' % op_for_event_logs.id
        assert os.path.isfile(target_path)
        try:
            with open(target_path, 'rb') as log_file:
                recorded_log = json.load(log_file)
            assert recorded_log == want
        finally:
            os.remove(target_path)

    @mock.patch.object(Operation, '_emit_state_change_event')
    def test_no_state_change_event_on_instantiation(self, mock_emit_state_change_method, fake_event_svc, adversary):
        Operation(name='test', agents=[], adversary=adversary)
        mock_emit_state_change_method.assert_not_called()

    @mock.patch.object(Operation, '_emit_state_change_event')
    def test_no_state_change_event_fired_when_setting_same_state(self, mock_emit_state_change_method, fake_event_svc,
                                                                 adversary):
        initial_state = 'running'
        op = Operation(name='test', agents=[], adversary=adversary, state=initial_state)
        op.state = initial_state
        mock_emit_state_change_method.assert_not_called()

    @mock.patch.object(Operation, '_emit_state_change_event')
    def test_state_change_event_fired_on_state_change(self, mock_emit_state_change_method, fake_event_svc, adversary):
        op = Operation(name='test', agents=[], adversary=adversary, state='running')
        op.state = 'finished'
        mock_emit_state_change_method.assert_called_with(from_state='running', to_state='finished')

    def test_emit_state_change_event(self, loop, fake_event_svc, adversary):
        op = Operation(name='test', agents=[], adversary=adversary, state='running')
        fake_event_svc.reset()

        loop.run_until_complete(
            op._emit_state_change_event(
                from_state='running',
                to_state='finished'
            )
        )

        expected_key = (Operation.EVENT_EXCHANGE, Operation.EVENT_QUEUE_STATE_CHANGED)
        assert expected_key in fake_event_svc.fired

        event_kwargs = fake_event_svc.fired[expected_key]
        assert event_kwargs['op'] == op.id
        assert event_kwargs['from_state'] == 'running'
        assert event_kwargs['to_state'] == 'finished'

    def test_with_learning_parser(self, loop, contact_svc, data_svc, learning_svc, event_svc, op_with_learning_parser,
                                  make_test_link, make_test_result, knowledge_svc):
        test_link = make_test_link(1234)
        op_with_learning_parser.add_link(test_link)
        test_result = make_test_result(test_link.id)
        loop.run_until_complete(data_svc.store(op_with_learning_parser))
        loop.run_until_complete(contact_svc._save(test_result))
        assert len(test_link.facts) == 1
        fact = test_link.facts[0]
        assert fact.trait == 'host.ip.address'
        assert fact.value == '10.10.10.10'
        knowledge_data = loop.run_until_complete(op_with_learning_parser.all_facts())
        assert len(knowledge_data) == 1
        assert knowledge_data[0].trait == 'host.ip.address'
        assert knowledge_data[0].value == '10.10.10.10'

    def test_without_learning_parser(self, loop, app_svc, contact_svc, data_svc, learning_svc, event_svc,
                                     op_without_learning_parser, make_test_link, make_test_result):
        app_svc = app_svc(loop)  # contact_svc._save(...) needs app service registered
        test_link = make_test_link(5678)
        op_without_learning_parser.add_link(test_link)
        test_result = make_test_result(test_link.id)
        loop.run_until_complete(data_svc.store(op_without_learning_parser))
        loop.run_until_complete(contact_svc._save(test_result))
        assert len(test_link.facts) == 0

    def test_facts(self, loop, app_svc, contact_svc, file_svc, data_svc, learning_svc, event_svc,
                   op_with_learning_and_seeded, make_test_link, make_test_result, knowledge_svc):
        test_link = make_test_link(9876)
        op_with_learning_and_seeded.add_link(test_link)

        test_result = make_test_result(test_link.id)
        loop.run_until_complete(data_svc.store(op_with_learning_and_seeded))
        loop.run_until_complete(op_with_learning_and_seeded._init_source())  # need to call this manually (no 'run')
        loop.run_until_complete(contact_svc._save(test_result))
        assert len(test_link.facts) == 1
        fact = test_link.facts[0]
        assert fact.trait == 'host.ip.address'
        assert fact.value == '10.10.10.10'

        knowledge_data = loop.run_until_complete(op_with_learning_and_seeded.all_facts())
        assert len(knowledge_data) == 2
        origin_set = [x.source for x in knowledge_data]
        assert op_with_learning_and_seeded.id in origin_set
        assert op_with_learning_and_seeded.source.id in origin_set

        report = loop.run_until_complete(op_with_learning_and_seeded.report(file_svc, data_svc))
        assert len(report['facts']) == 2
