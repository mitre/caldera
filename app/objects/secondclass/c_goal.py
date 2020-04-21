from app.utility.base_object import BaseObject


class Goal(BaseObject):

    def satisfied(self, all_facts=None):
        temp_count = 0
        if all_facts:
            for fact in all_facts:
                if self.target == fact.trait and self.value == fact.value:
                    temp_count += 1
        if temp_count >= self.count:
            self.achieved = True
        return self.achieved

    @property
    def display(self):
        return dict(target=self.target, value=self.value, count=self.count, satisfied=self.achieved)

    def __init__(self, target, value, count=2**20):
        super().__init__()
        self.target = target
        self.value = value
        self.count = count
        self.achieved = False
