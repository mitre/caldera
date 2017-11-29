import unittest
from caldera.app.logic.planner import PlannerContext, eval_plan
from caldera.app.logic.logic import Term
from caldera.app.operation.operation_steps import all_steps
from caldera.app.operation.operation import _database_objs
from caldera.app.operation.step import OPShare
from caldera.app.logic.pydatalog_logic import DatalogContext as LogicContext
# import logging
# pyEngine.Logging = True
# logging.basicConfig(level=logging.INFO)


class TestInfinitePlanner(unittest.TestCase):
    def setUp(self):
        self.context = PlannerContext(LogicContext())
        for obj in _database_objs:
            primary = obj != OPShare
            self.context.define_type(obj.__name__, primary=primary)

    def tearDown(self):
        self.context.close()

    def test_infinite(self):
        # this code converts all of the steps in all_steps
        for step in all_steps:
            new_action = self.context.add_step(step)
            print(new_action.name)
            print("Parameters:")
            for item in sorted(new_action.parameters, key=lambda x: str(x)):
                print("         ", item)
            print("Significant Parameters:")
            for item in sorted(new_action.significant_parameters, key=lambda x:str(x)):
                print("         ", item)
            print("Preconditions:")
            for item in sorted(new_action.requirements, key=lambda x: str(x)):
                print("         ", item)
            print("Postconditions:")
            for item in sorted(new_action.add):
                print("       + ", item)
            for item in sorted(new_action.delete):
                print("       - ", item)
            print("")

        # these satisfy get_domain
        self.context.assert_fact(Term('opexec(some_rat)'))
        self.context.assert_fact(Term('ophost(current_host)'))
        self.context.assert_fact(Term('has_property', 'some_rat', 'elevated', True))
        self.context.assert_fact(Term('has_property(some_rat, host, current_host)'))
        self.context.assert_fact(Term('has_property', 'some_rat', 'executable', 'C:\\commander.exe'))

        total_actions = 50
        plan_length = 3
        print(self.context.uncommitted_actions)

        format_str = "{!s:<5} {!s:<5} {!s:<5} {!s:<15} {}"
        print(format_str.format("plans", 'facts', "score", "action", "parameters"))
        while total_actions > 0:
            old_plans = self.context.plan(None, plan_length)
            countnone = 0
            for item in old_plans:
                if not item:
                    countnone += 1
            assert countnone == 0

            if len(old_plans) == 0:
                print("len == 0")
                print("")
                print("Ran out of plans, dumping facts:")
                self.context.print_dump()
                return
            else:
                best_plan_action = self.context.actions[old_plans[0][0][0]]
                best_plan_parameters = old_plans[0][0][1]
                best_plan_score = eval_plan(old_plans[0])

                print(format_str.format(str(len(old_plans))[:5], str(len(self.context.facts))[:5],
                      str(best_plan_score)[:5], best_plan_action.name[:15], best_plan_parameters))

                #   find the new plan length
                num_old_plans = len(old_plans)
                new_plan_length = plan_length
                if num_old_plans < 50:
                    new_plan_length = plan_length + 1
                if num_old_plans > 1000:
                    new_plan_length = plan_length - 1
                if new_plan_length == 0:
                    new_plan_length = 1
                if new_plan_length != plan_length:
                    plan_length = new_plan_length
                    print("--> new length:  ", new_plan_length)

                self.context.do_action(best_plan_action, *best_plan_parameters)
                total_actions -= 1
