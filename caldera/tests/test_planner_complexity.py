import unittest
import time
import logging
import cProfile as profile
from caldera.app.logic.planner import PlannerContext, eval_plan
from caldera.app.logic.logic import Term
from caldera.app.operation.operation_steps import all_steps
from caldera.app.operation.operation import _database_objs, OPShare
from caldera.app.util import relative_path
from caldera.app.logic.pydatalog_logic import DatalogContext as LogicContext

logging.basicConfig(level=logging.DEBUG)


class TestPlanner(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        with open(relative_path(__file__, '10_host_dataset.txt')) as f:
            dataset = f.readlines()

        self.dataset = []
        for fact in sorted(dataset, key=lambda x: x.count(',')):
            term = Term(fact.strip())
            term.literals = list(True if x == "True" else False if x == "False" else x for x in term.literals)
            self.dataset.append(term)

        super().__init__(*args, **kwargs)

    def setUp(self):
        self.context = PlannerContext(LogicContext())

    def tearDown(self):
        self.context.close()

    def test_main(self):
        # pr = profile.Profile()
        # pr.disable()

        # this code converts all of the steps in all_steps
        for step in all_steps:
            if step.__name__ in ["GetComputers", "WMI_remote_pc", "Copy", "Credentials", "GetAdmin", "GetDomain",
                                 "HKLMRunKeyPersist", "NetUse"]:
                self.context.add_step(step)

        # load types into the planner
        for obj in _database_objs:
            primary = obj != OPShare
            self.context.define_type(obj.__name__, primary=primary)

        for fact in self.dataset:
            self.context.assert_fact(fact)

        format_str = "{!s:<5} {!s:<5} {!s:<5} {!s:<15} {}"

        plan_length = 2
        t1 = time.process_time()

        #pr.enable()
        plans = self.context.plan(None, plan_length)
        #pr.disable()

        t2 = time.process_time()
        print("Planning time took: {} seconds".format(t2 - t1))
        #pr.dump_stats('profile.pstat')

        countnone = 0
        for item in plans:
            if not item:
                countnone += 1
        assert countnone == 0

        if len(plans) == 0:
            print("len == 0")
            print("")
            print("Ran out of plans, dumping facts:")
            self.context.print_dump()
        else:
            best_plan_action = self.context.actions[plans[0][0][0]]
            best_plan_parameters = plans[0][0][1]
            best_plan_score = eval_plan(plans[0])

            print(format_str.format("plans", 'facts', "score", "action", "parameters"))
            print(format_str.format(str(len(plans))[:5], str(len(self.context.facts))[:5],
                  str(best_plan_score)[:5], best_plan_action.name[:15], best_plan_parameters))

            self.print_plan(plans[0])

    def print_plan(self, plan):
        def print_action(action, parameters):
            print("{}{}".format(action.name, parameters))

        for step in plan:
            action = self.context.actions[step[0]]
            parameters = step[1]
            print_action(action, parameters)
            print(" -> ")
