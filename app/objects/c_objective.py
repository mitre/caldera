import uuid

import marshmallow as ma

from app.objects.interfaces.i_object import FirstClassObjectInterface
from app.objects.secondclass.c_goal import GoalSchema
from app.utility.base_object import BaseObject


class ObjectiveSchema(ma.Schema):

    class Meta:
        unknown = ma.EXCLUDE

    id = ma.fields.String()
    name = ma.fields.String()
    description = ma.fields.String()
    goals = ma.fields.List(ma.fields.Nested(GoalSchema))
    percentage = ma.fields.Float(dump_only=True)

    @ma.pre_load
    def remove_properties(self, data, **_):
        data.pop('percentage', None)
        return data

    @ma.post_load
    def build_objective(self, data, **kwargs):
        return None if kwargs.get('partial') is True else Objective(**data)


class Objective(FirstClassObjectInterface, BaseObject):

    schema = ObjectiveSchema()

    @property
    def unique(self):
        return self.hash('%s' % self.id)

    @property
    def percentage(self):
        if len(self.goals) > 0:
            return 100 * (len([g for g in self.goals if g.satisfied() is True])/len(self.goals))
        return 0

    def completed(self, facts=None):
        return not any(x.satisfied(facts) is False for x in self.goals)

    def __init__(self, id='', name='', description='', goals=None):
        super().__init__()
        self.id = id if id else str(uuid.uuid4())
        self.name = name
        self.description = description
        self.goals = goals if goals else []

    def store(self, ram):
        existing = self.retrieve(ram['objectives'], self.unique)
        if not existing:
            ram['objectives'].append(self)
            return self.retrieve(ram['objectives'], self.unique)
        existing.update('name', self.name)
        existing.update('description', self.description)
        existing.update('goals', self.goals)
        return existing
