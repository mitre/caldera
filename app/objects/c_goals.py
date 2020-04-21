from app.objects.secondclass.c_goal import Goal
from app.utility.base_object import BaseObject


class Goals(BaseObject):
    def __init__(self, goal_list=list()):
        super().__init__()
        self.to_fulfill = list()
        for goal in goal_list:
            new_goal = Goal(target=goal.target, value=goal.value, count=goal.count)
            self.to_fulfill.append(new_goal)
        if len(self.to_fulfill) == 0:
            self.to_fulfill.append(Goal(target='exhaustion', value='complete'))

    def satisfied(self, facts=None):
        return not any(x.satisfied(facts) == False for x in self.to_fulfill)

    @property
    def percentage(self):
        return 100 * float(len([x for x in self.to_fulfill if x.satisfied == True])) / float(len(self.to_fulfill))

    def display(self):
        return dict(goal_list=[x.display for x in self.to_fulfill], percentage=self.percentage)