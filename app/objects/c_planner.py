import os

from app.utility.base_object import BaseObject
from app.objects.secondclass.c_fact import Fact


class Planner(BaseObject):

    @property
    def unique(self):
        return self.hash(self.name)

    @property
    def display(self):
        return dict(name=self.name, module=self.module, params=self.params, description=self.description,
                    stopping_conditions=[fact.display for fact in self.stopping_conditions])

    def __init__(self, planner_id, name, module, params, stopping_conditions=None, description=None,
                 ignore_enforcement_modules=()):
        super().__init__()
        self.planner_id = planner_id
        self.name = name
        self.module = module
        self.params = params
        self.description = description
        self.stopping_conditions = self._set_stopping_conditions(stopping_conditions)
        self.ignore_enforcement_modules = ignore_enforcement_modules

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
            return [Fact(trait, value) for sc in conditions for trait, value in sc.items()]
        return []
