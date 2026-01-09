
import pytest
from unittest.mock import AsyncMock

from app.planners.atomic import LogicalPlanner


class AdversaryStub():
    atomic_ordering = ['ability_a', 'ability_b', 'ability_c']


class OperationStub():
    def __init__(self):
        self.adversary = AdversaryStub()
        self.agents = ['agent_1']
        self.wait_for_links_completion = AsyncMock()
        self.apply = AsyncMock(side_effect=self._apply_side_effect)

    def _apply_side_effect(self, value):
        return value.id


class PlanningSvcStub():
    def __init__(self):
        self.get_links = AsyncMock()

    def set_link_return(self, links):
        self.get_links = AsyncMock(return_value=links)


class AbilityStub():
    def __init__(self, ability_id):
        self.ability_id = ability_id


class LinkStub():
    def __init__(self, ability_id):
        self.ability = AbilityStub(ability_id)
        self.id = 'link_' + ability_id

    def __eq__(self, other):
        return self.ability.ability_id == other.ability.ability_id and self.id == other.id


@pytest.fixture
def atomic_planner():
    planner = LogicalPlanner(
        operation=OperationStub(),
        planning_svc=PlanningSvcStub()
    )

    return planner


class TestAtomic():

    def test_atomic_with_links_in_order(self, event_loop, atomic_planner):

        atomic_planner.planning_svc.set_link_return(
            links=[
                LinkStub('ability_b'),
                LinkStub('ability_c')
            ]
        )

        event_loop.run_until_complete(atomic_planner.atomic())

        assert atomic_planner.operation.apply.call_count == 1
        assert atomic_planner.operation.wait_for_links_completion.call_count == 1
        atomic_planner.operation.apply.assert_awaited_with(LinkStub('ability_b'))
        atomic_planner.operation.wait_for_links_completion.assert_awaited_with(['link_ability_b'])

    def test_atomic_with_links_out_of_order(self, event_loop, atomic_planner):

        atomic_planner.planning_svc.set_link_return(
            links=[
                LinkStub('ability_c'),
                LinkStub('ability_b')
            ]
        )

        event_loop.run_until_complete(atomic_planner.atomic())

        assert atomic_planner.operation.apply.call_count == 1
        assert atomic_planner.operation.wait_for_links_completion.call_count == 1
        atomic_planner.operation.apply.assert_awaited_with(LinkStub('ability_b'))
        atomic_planner.operation.wait_for_links_completion.assert_awaited_with(['link_ability_b'])

    def test_atomic_no_links(self, event_loop, atomic_planner):

        atomic_planner.planning_svc.set_link_return(
            links=[]
        )

        event_loop.run_until_complete(atomic_planner.atomic())

        assert atomic_planner.next_bucket is None
        assert atomic_planner.operation.apply.call_count == 0
        assert atomic_planner.operation.wait_for_links_completion.call_count == 0
