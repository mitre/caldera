import os

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

    @ma.post_load()
    def build_planner(self, data, **_):
        return Planner(**data)


class Planner(FirstClassObjectInterface, BaseObject):

    schema = PlannerSchema()
    display_schema = PlannerSchema(exclude=['planner_id', 'ignore_enforcement_modules'])

    @property
    def unique(self):
        return self.hash(self.name)

    def __init__(self, planner_id, name, module, params, stopping_conditions=None, description=None,
                 ignore_enforcement_modules=(), allow_repeatable_abilities=False):
        super().__init__()
        self.planner_id = planner_id
        self.name = name
        self.module = module
        self.params = params
        self.description = description
        self.stopping_conditions = self._set_stopping_conditions(stopping_conditions)
        self.ignore_enforcement_modules = ignore_enforcement_modules
        self.allow_repeatable_abilities = allow_repeatable_abilities

    def store(self, ram):
        existing = self.retrieve(ram['planners'], self.unique)
        if not existing:
            ram['planners'].append(self)
            return self.retrieve(ram['planners'], self.unique)
        else:
            existing.update('stopping_conditions', self.stopping_conditions)
            existing.update('params', self.params)
        return existing

    async def which_plugin(self):
        for plugin in os.listdir('plugins'):
            if await self.walk_file_path(os.path.join('plugins', plugin, 'data', ''), '%s.yml' % self.planner_id):
                return plugin
        return None

    """ PRIVATE """

    @staticmethod
    def _set_stopping_conditions(conditions):
        if conditions:
            return [Fact.load(dict(trait=trait, value=value)) for sc in conditions for trait, value in sc.items()]
        return []
