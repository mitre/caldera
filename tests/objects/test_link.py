from unittest import mock

import pytest

from app.objects.secondclass.c_link import Link
from app.objects.secondclass.c_fact import Fact
from app.service.interfaces.i_event_svc import EventServiceInterface
from app.utility.base_service import BaseService


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

    service.remove_service('event_svc')


class TestLink:

    def test_link_eq(self, ability, executor):
        test_executor = executor(name='psh', platform='windows')
        test_ability = ability(ability_id='123', executors=[test_executor])
        fact = Fact(trait='remote.host.fqdn', value='dc')
        executor_changes = dict(
            executor='psh',
            action='update-path',
            value='C:\\Users\\Public\\p2.exe'
        )
        test_link = Link(command='sc.exe \\dc create sandsvc binpath= "s4ndc4t.exe -originLinkID 111111"',
                         paw='123456', ability=test_ability, id=111111, executor=test_executor,
                         executor_changes=executor_changes)
        test_link.used = [fact]
        test_link2 = Link(command='sc.exe \\dc create sandsvc binpath= "s4ndc4t.exe -originLinkID 222222"',
                          paw='123456', ability=test_ability, id=222222, executor=test_executor,
                          executor_changes=executor_changes)
        test_link2.used = [fact]
        assert test_link == test_link2

    def test_link_neq(self, ability, executor):
        test_executor = executor(name='psh', platform='windows')
        test_ability = ability(ability_id='123', executors=[test_executor])
        fact_a = Fact(trait='host.user.name', value='a')
        fact_b = Fact(trait='host.user.name', value='b')
        test_link_a = Link(command='net user a', paw='123456', ability=test_ability, id=111111, executor=test_executor)
        test_link_a.used = [fact_a]
        test_link_b = Link(command='net user b', paw='123456', ability=test_ability, id=222222, executor=test_executor)
        test_link_b.used = [fact_b]
        assert test_link_a != test_link_b

    @mock.patch.object(Link, '_emit_status_change_event')
    def test_no_status_change_event_on_instantiation(self, mock_emit_status_change_method, ability, executor):
        executor = executor('psh', 'windows')
        ability = ability(executor=executor)
        Link(command='net user a', paw='123456', ability=ability, executor=executor)
        mock_emit_status_change_method.assert_not_called()

    @mock.patch.object(Link, '_emit_status_change_event')
    def test_no_status_change_event_fired_when_setting_same_status(self, mock_emit_status_change_method, ability, executor):
        executor = executor('psh', 'windows')
        ability = ability(executor=executor)
        link = Link(command='net user a', paw='123456', ability=ability, executor=executor, status=-3)
        link.status = link.status
        mock_emit_status_change_method.assert_not_called()

    @mock.patch.object(Link, '_emit_status_change_event')
    def test_status_change_event_fired_on_status_change(self, mock_emit_status_change_method, ability, executor):
        executor = executor('psh', 'windows')
        ability = ability(executor=executor)
        link = Link(command='net user a', paw='123456', ability=ability, executor=executor, status=-3)
        link.status = -5
        mock_emit_status_change_method.assert_called_with(from_status=-3, to_status=-5)

    def test_emit_status_change_event(self, loop, fake_event_svc, ability, executor):
        executor = executor('psh', 'windows')
        ability = ability(executor=executor)
        link = Link(command='net user a', paw='123456', ability=ability, executor=executor, status=-3)
        fake_event_svc.reset()

        loop.run_until_complete(
            link._emit_status_change_event(
                from_status=-3,
                to_status=-5
            )
        )

        expected_key = (Link.EVENT_EXCHANGE, Link.EVENT_QUEUE_STATUS_CHANGED)
        assert expected_key in fake_event_svc.fired

        event_kwargs = fake_event_svc.fired[expected_key]
        assert event_kwargs['link'] == link.id
        assert event_kwargs['from_status'] == -3
        assert event_kwargs['to_status'] == -5

    def test_link_agent_reported_time_not_present_when_none_roundtrip(self, ability, executor):
        test_executor = executor(name='psh', platform='windows')
        test_ability = ability(ability_id='123')
        test_link = Link(command='sc.exe \\dc create sandsvc binpath= "s4ndc4t.exe -originLinkID 111111"',
                         paw='123456', ability=test_ability, executor=test_executor, id=111111)
        serialized_link = test_link.display
        loaded_link = Link.load(serialized_link)

        assert 'agent_reported_time' not in serialized_link
        assert loaded_link.agent_reported_time is None

    def test_link_agent_reported_time_present_when_set_roundtrip(self, ability, executor):
        test_executor = executor(name='psh', platform='windows')
        test_ability = ability(ability_id='123')
        test_link = Link(command='sc.exe \\dc create sandsvc binpath= "s4ndc4t.exe -originLinkID 111111"',
                         paw='123456', ability=test_ability, executor=test_executor, id=111111,
                         agent_reported_time=BaseService.get_timestamp_from_string('2021-02-23 11:50:16'))
        serialized_link = test_link.display
        loaded_link = Link.load(serialized_link)

        assert serialized_link['agent_reported_time'] == '2021-02-23 11:50:16'
        assert loaded_link.agent_reported_time == BaseService.get_timestamp_from_string('2021-02-23 11:50:16')
