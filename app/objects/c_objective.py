import marshmallow as ma

from app.objects.interfaces.i_object import FirstClassObjectInterface
from app.objects.secondclass.c_goal import GoalSchema
from app.utility.base_object import BaseObject


class ObjectiveSchema(ma.Schema):

    id = ma.fields.String()
    name = ma.fields.String()
    goals = ma.fields.List(ma.fields.Nested(GoalSchema()))

    @ma.post_load
    def build_objective(self, data, **_):
        return Objective(**data)


class Objective(FirstClassObjectInterface, BaseObject):

    schema = ObjectiveSchema()

    @property
    def unique(self):
        return self.hash('%s' % self.id)

    @property
    def percentage(self):
        return 100 * (len([g for g in self.goals if g.satisfied() is True])/len(self.goals))

    def completed(self, facts=None):
        return not any(x.satisfied(facts) is False for x in self.goals)

    def __init__(self, id='', name='', goals=None):
        super().__init__()
        self.id = id
        self.name = name
        self.goals = goals if goals else []

    def store(self, ram):
        existing = self.retrieve(ram['objectives'], self.unique)
        if not existing:
            ram['objectives'].append(self)
            return self.retrieve(ram['objectives'], self.unique)
        existing.update('name', self.name)
        existing.update('goals', self.goals)
        return existing
