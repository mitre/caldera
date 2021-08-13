from unittest import mock

import pytest

from app.objects.secondclass.c_link import Link
from app.objects.secondclass.c_fact import Fact
from app.objects.secondclass.c_relationship import Relationship
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
        test_link = Link(command='sc.exe \\dc create sandsvc binpath= "s4ndc4t.exe -originLinkID 111111"',
                         paw='123456', ability=test_ability, id=111111, executor=test_executor)
        test_link.used = [fact]
        test_link2 = Link(command='sc.exe \\dc create sandsvc binpath= "s4ndc4t.exe -originLinkID 222222"',
                          paw='123456', ability=test_ability, id=222222, executor=test_executor)
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

    def test_link_knowledge_svc_synchronization(self, loop, executor, ability, knowledge_svc):
        test_executor = executor(name='psh', platform='windows')
        test_ability = ability(ability_id='123', executors=[test_executor])
        fact = Fact(trait='remote.host.fqdn', value='dc')
        fact2 = Fact(trait='domain.user.name', value='Bob')
        relationship = Relationship(source=fact, edge='has_admin', target=fact2)
        test_link = Link(command='echo "this was a triumph"',
                         paw='123456', ability=test_ability, id=111111, executor=test_executor)

        loop.run_until_complete(test_link._create_relationships([relationship], None))
        checkable = [(x.trait, x.value) for x in test_link.facts]
        assert (fact.trait, fact.value) in checkable
        assert (fact2.trait, fact2.value) in checkable
        knowledge_base_f = loop.run_until_complete(knowledge_svc.get_facts(dict(source=test_link.id)))
        assert len(knowledge_base_f) == 2
        assert test_link.id in knowledge_base_f[0].links
        knowledge_base_r = loop.run_until_complete(knowledge_svc.get_relationships(dict(edge='has_admin')))
        assert len(knowledge_base_r) == 1
