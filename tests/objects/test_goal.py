from app.objects.secondclass.c_goal import Goal
from app.objects.secondclass.c_fact import Fact


class TestGoal:

    def test_satisfied(self):
        test_goal = Goal(target='target', value='value', count=1)
        assert test_goal.satisfied() is False
        assert test_goal.satisfied(all_facts=[Fact(trait='target', value='value')]) is True

    def test_multi_satisified(self):
        test_goal = Goal(target='target', value='value', count=3)
        test_fact = Fact(trait='target', value='value')
        assert test_goal.satisfied(all_facts=[test_fact]) is False
        assert test_goal.satisfied(all_facts=[test_fact, test_fact, test_fact]) is True
