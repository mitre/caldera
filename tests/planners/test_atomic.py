
from tests import AsyncMock

import pytest

from app.planners.atomic import LogicalPlanner


class AdversaryStub():
    atomic_ordering = ['ability_a', 'ability_b', 'ability_c']


class AdversaryDictStub():
    atomic_ordering = [
        {'ability_id': 'ability_a', 'metadata': {}},
        {'ability_id': 'ability_b', 'metadata': {'executor_facts': {'linux': []}}},
        {'ability_id': 'ability_c', 'metadata': {}},
    ]


class OperationStub():
    def __init__(self, adversary=None):
        self.adversary = adversary or AdversaryStub()
        self.agents = ['agent_1']
        self.wait_for_links_completion = AsyncMock()
        self.apply = AsyncMock()


class PlanningSvcStub():
    def __init__(self):
        self.get_links = AsyncMock()

    def set_link_return(self, links):
        self.get_links = AsyncMock(return_value=links)


class AbilityStub():
    def __init__(self, ability_id):
        self.ability_id = ability_id


class LinkStub():
    def __init__(self, ability_id, step_idx=None):
        self.ability = AbilityStub(ability_id)
        if step_idx is not None:
            self.step_idx = step_idx

    def __eq__(self, other):
        return self.ability.ability_id == other.ability.ability_id


@pytest.fixture
def atomic_planner():
    planner = LogicalPlanner(
        operation=OperationStub(),
        planning_svc=PlanningSvcStub()
    )

    return planner


@pytest.fixture
def atomic_planner_dict_steps():
    planner = LogicalPlanner(
        operation=OperationStub(adversary=AdversaryDictStub()),
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
        atomic_planner.operation.apply.assert_called_with(LinkStub('ability_b'))
        atomic_planner.operation.wait_for_links_completion.assert_called_with([LinkStub('ability_b')])

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
        atomic_planner.operation.apply.assert_called_with(LinkStub('ability_b'))
        atomic_planner.operation.wait_for_links_completion.assert_called_with([LinkStub('ability_b')])

    def test_atomic_no_links(self, event_loop, atomic_planner):

        atomic_planner.planning_svc.set_link_return(
            links=[]
        )

        event_loop.run_until_complete(atomic_planner.atomic())

        assert atomic_planner.next_bucket is None
        assert atomic_planner.operation.apply.call_count == 0
        assert atomic_planner.operation.wait_for_links_completion.call_count == 0


class TestAtomicDictSteps():
    """Tests for the atomic planner when adversary uses dict-style steps with embedded metadata."""

    def test_get_next_atomic_link_by_step_idx(self, event_loop, atomic_planner_dict_steps):
        """step_idx-based selection: should pick the link whose step_idx matches the
        first position in atomic_ordering that has a corresponding link."""
        links = [
            LinkStub('ability_b', step_idx=1),
            LinkStub('ability_c', step_idx=2),
        ]
        result = event_loop.run_until_complete(
            atomic_planner_dict_steps._get_next_atomic_link(links)
        )
        assert result.ability.ability_id == 'ability_b'

    def test_get_next_atomic_link_step_idx_first_wins(self, event_loop, atomic_planner_dict_steps):
        """When step_idx 0 link is available, it should be preferred over later steps."""
        links = [
            LinkStub('ability_a', step_idx=0),
            LinkStub('ability_b', step_idx=1),
        ]
        result = event_loop.run_until_complete(
            atomic_planner_dict_steps._get_next_atomic_link(links)
        )
        assert result.ability.ability_id == 'ability_a'

    def test_get_next_atomic_link_fallback_to_ability_id(self, event_loop, atomic_planner_dict_steps):
        """If links don't carry step_idx, fall back to ability_id matching."""
        links = [
            LinkStub('ability_c'),
            LinkStub('ability_b'),
        ]
        result = event_loop.run_until_complete(
            atomic_planner_dict_steps._get_next_atomic_link(links)
        )
        assert result.ability.ability_id == 'ability_a' or result.ability.ability_id == 'ability_b'

    def test_get_next_atomic_link_fallback_ordering_preserved(self, event_loop, atomic_planner_dict_steps):
        """Fallback ability_id match should respect atomic_ordering sequence (ability_a before ability_b)."""
        links = [
            LinkStub('ability_b'),
            LinkStub('ability_a'),
        ]
        result = event_loop.run_until_complete(
            atomic_planner_dict_steps._get_next_atomic_link(links)
        )
        assert result.ability.ability_id == 'ability_a'

    def test_atomic_dict_steps_runs_first_available(self, event_loop, atomic_planner_dict_steps):
        """Full atomic() run with dict steps should apply the first matching link."""
        atomic_planner_dict_steps.planning_svc.set_link_return(
            links=[
                LinkStub('ability_b', step_idx=1),
                LinkStub('ability_c', step_idx=2),
            ]
        )
        event_loop.run_until_complete(atomic_planner_dict_steps.atomic())
        assert atomic_planner_dict_steps.operation.apply.call_count == 1
        atomic_planner_dict_steps.operation.apply.assert_called_with(LinkStub('ability_b'))

    def test_atomic_dict_steps_no_links(self, event_loop, atomic_planner_dict_steps):
        """No available links should set next_bucket to None."""
        atomic_planner_dict_steps.planning_svc.set_link_return(links=[])
        event_loop.run_until_complete(atomic_planner_dict_steps.atomic())
        assert atomic_planner_dict_steps.next_bucket is None
