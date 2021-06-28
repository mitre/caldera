import marshmallow as ma

from app.utility.base_object import BaseObject


class GoalSchema(ma.Schema):

    target = ma.fields.String()
    value = ma.fields.String()
    count = ma.fields.Integer()
    operator = ma.fields.String()
    achieved = ma.fields.Boolean(dump_only=True)

    @ma.pre_load
    def remove_properties(self, data, **_):
        data.pop('achieved', None)
        return data

    @ma.post_load
    def build_goal(self, data, **_):
        return Goal(**data)


class Goal(BaseObject):

    schema = GoalSchema()
    MAX_GOAL_COUNT = 2**20

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
        if operator == '*':
            return lambda x, y: True
        return lambda x, y: x == y

    def satisfied(self, all_facts=None):
        temp_count = 0
        for fact in (all_facts or []):
            if self.target == fact.trait and self.parse_operator(self.operator)(self.value, fact.value):
                temp_count += 1
        if temp_count >= self.count:
            self.achieved = True
        return self.achieved

    def __init__(self, target='exhaustion', value='complete', count=None, operator='=='):
        super().__init__()
        self.target = target
        self.value = value
        self.count = count if count is not None else self.MAX_GOAL_COUNT
        self.achieved = False
        self.operator = operator
