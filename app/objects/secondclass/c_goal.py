from app.utility.base_object import BaseObject


class Goal(BaseObject):

    @staticmethod
    def parse_operator(operator):
        if operator == '<':
            return lambda x, y: x < y
        if operator == '>':
            return lambda x, y: x > y
        if operator == '<=':
            return lambda x, y: x <= y
        if operator == '>=':
            return lambda x, y: x >= y
        if operator == 'in':
            return lambda x, y: x in y
        return lambda x, y: x == y

    def satisfied(self, all_facts=None):
        temp_count = 0
        if all_facts:
            for fact in all_facts:
                if self.target == fact.trait and self.parse_operator(self.operator)(self.value, fact.value):
                    temp_count += 1
        if temp_count >= self.count:
            self.achieved = True
        return self.achieved

    @property
    def display(self):
        return dict(target=self.target, value=self.value, count=self.count,
                    operator=self.operator, satisfied=self.achieved)

    def __init__(self, target, value, count=2**20, operator=None):
        super().__init__()
        self.target = target
        self.value = value
        self.count = count
        self.achieved = False
        self.operator = operator
