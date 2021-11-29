import uuid

import marshmallow as ma

from app.objects.interfaces.i_object import FirstClassObjectInterface
from app.utility.base_object import BaseObject
from app.objects.secondclass.c_fact import Fact, FactSchema


class PlannerSchema(ma.Schema):
    planner_id = ma.fields.String(data_key='id')
    name = ma.fields.String()
    module = ma.fields.String()
    params = ma.fields.Dict()
    description = ma.fields.String()
    stopping_conditions = ma.fields.List(ma.fields.Nested(FactSchema()))
    ignore_enforcement_modules = ma.fields.List(ma.fields.String())
    allow_repeatable_abilities = ma.fields.Boolean()
    plugin = ma.fields.String(missing=None)

    @ma.post_load()
    def build_planner(self, data, **kwargs):
        return None if kwargs.get('partial') is True else Planner(**data)


class Planner(FirstClassObjectInterface, BaseObject):

    schema = PlannerSchema()
    display_schema = PlannerSchema(exclude=['module', 'ignore_enforcement_modules'])

    @property
    def unique(self):
        return self.hash(self.name)

    def __init__(self, name='', planner_id='', module='', params=None, stopping_conditions=None, description=None,
                 ignore_enforcement_modules=(), allow_repeatable_abilities=False, plugin=''):
        super().__init__()
        self.name = name
        self.planner_id = planner_id if planner_id else str(uuid.uuid4())
        self.module = module
        self.params = params if params else {}
        self.description = description
        self.stopping_conditions = self._set_stopping_conditions(stopping_conditions)
        self.ignore_enforcement_modules = ignore_enforcement_modules
        self.allow_repeatable_abilities = allow_repeatable_abilities
        self.plugin = plugin

    def store(self, ram):
        existing = self.retrieve(ram['planners'], self.unique)
        if not existing:
            ram['planners'].append(self)
            return self.retrieve(ram['planners'], self.unique)
        else:
            existing.update('stopping_conditions', self.stopping_conditions)
            existing.update('params', self.params)
            existing.update('plugin', self.plugin)
        return existing

    async def which_plugin(self):
        return self.plugin

    @staticmethod
    def _set_stopping_conditions(conditions):
        if conditions:
            return [Fact.load(dict(trait=trait, value=value)) for sc in conditions for trait, value in sc.items()]
        return []
