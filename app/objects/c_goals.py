from app.objects.interfaces.i_object import FirstClassObjectInterface
from app.objects.secondclass.c_goal import Goal
from app.utility.base_object import BaseObject


class Goals(FirstClassObjectInterface, BaseObject):
    def __init__(self, goal_list=None):
        super().__init__()
        self.to_fulfill = list()
        if goal_list:
            for goal in goal_list:
                new_goal = Goal(target=goal.target, value=goal.value, count=goal.count, operator=goal.operator)
                self.to_fulfill.append(new_goal)
        else:
            self.to_fulfill.append(Goal(target='exhaustion', value='complete'))

    def satisfied(self, facts=None):
        return not any(x.satisfied(facts) is False for x in self.to_fulfill)

    @property
    def percentage(self):
        return 100 * len([x for x in self.to_fulfill if x.satisfied() is True]) / len(self.to_fulfill)

    def display(self):
        return dict(goal_list=[x.display for x in self.to_fulfill], percentage=self.percentage)
