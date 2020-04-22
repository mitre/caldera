from app.objects.secondclass.c_goal import Goal
from app.objects.c_goals import Goals
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

    def test_goals_satisfied(self):
        test_goal1 = Goal(target='target', value='value', count=1)
        test_goal2 = Goal(target='target2', value='value2', count=1)
        test_facta = Fact(trait='target', value='value')
        test_factb = Fact(trait='target2', value='value2')
        multi = Goals([test_goal1, test_goal2])
        assert multi.satisfied([test_facta]) is False
        assert multi.satisfied([test_facta, test_factb]) is True

    def test_goals_percent(self):
        test_goal1 = Goal(target='target', value='value', count=1)
        test_goal2 = Goal(target='target2', value='value2', count=1)
        test_fact = Fact(trait='target', value='value')
        multi = Goals([test_goal1, test_goal2])
        assert multi.satisfied([test_fact]) is False
        assert multi.percentage == 50
