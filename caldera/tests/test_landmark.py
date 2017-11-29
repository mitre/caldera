from unittest import TestCase
from caldera.app.operation.operation_steps import all_steps
from caldera.app.operation.operation import _database_objs, OPShare
from caldera.app.logic.planner import PlannerContext
from caldera.app.logic.landmark import get_landmarks
from caldera.app.logic.logic import Term, Variable
from caldera.app.logic.pydatalog_logic import DatalogContext as LogicContext


class TestGet_landmarks(TestCase):
    def setUp(self):
        self.context = PlannerContext(LogicContext())

    def tearDown(self):
        self.context.close()

    def test_get_landmarks(self):
        start = [Term('oprat', 'rat'), Term('ophost', 'starthost'), Term('has_property', 'rat', 'host', 'starthost'),
                 Term('ophost', 'goal_host')]

        A = Variable('A')
        goal = [Term('oprat', A), Term('has_property', A, 'host', 'goal_host')]

        for step in all_steps:
            if step.__name__ not in 'GetLocalProfiles':
                self.context.add_step(step)

        # load types into the planner
        for obj in _database_objs:
            primary = obj != OPShare
            self.context.define_type(obj.__name__, primary=primary)

        print(get_landmarks(start, goal, self.context.actions.values()))
