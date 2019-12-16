from app.utility.base_object import BaseObject
from app.objects.c_fact import Fact


class Planner(BaseObject):

    @property
    def unique(self):
        return self.hash(self.name)

    @property
    def display(self):
        return dict(name=self.name, module=self.module, params=self.params, description=self.description,
                    stopping_conditions=[fact.display for fact in self.stopping_conditions])

    def __init__(self, name, module, params, stopping_conditions=None, description=None):
        super().__init__()
        self.name = name
        self.module = module
        self.params = params
        self.description = description
        self.stopping_conditions = self._set_stopping_conditions(stopping_conditions)

    def store(self, ram):
        existing = self.retrieve(ram['planners'], self.unique)
        if not existing:
            ram['planners'].append(self)
            return self.retrieve(ram['planners'], self.unique)
        return existing

    """ PRIVATE """

    @staticmethod
    def _set_stopping_conditions(conditions):
        if conditions:
            return [Fact(trait, value) for sc in conditions for trait, value in sc.items()]
        return []
