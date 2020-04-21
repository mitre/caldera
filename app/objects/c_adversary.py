import os

from app.objects.interfaces.i_object import FirstClassObjectInterface
from app.utility.base_object import BaseObject
from app.objects.secondclass.c_goal import Goal


class Adversary(FirstClassObjectInterface, BaseObject):

    @property
    def unique(self):
        return self.hash('%s' % self.adversary_id)

    @property
    def display(self):
        return dict(adversary_id=self.adversary_id, name=self.name, description=self.description,
                    atomic_ordering=self.atomic_ordering, goals=[x.display for x in self.goals])

    def __init__(self, adversary_id, name, description, atomic_ordering, goals=list()):
        super().__init__()
        self.adversary_id = adversary_id
        self.name = name
        self.description = description
        self.atomic_ordering = atomic_ordering
        self.goals = goals

    def store(self, ram):
        existing = self.retrieve(ram['adversaries'], self.unique)
        if not existing:
            ram['adversaries'].append(self)
            return self.retrieve(ram['adversaries'], self.unique)
        existing.update('name', self.name)
        existing.update('description', self.description)
        existing.update('atomic_ordering', self.atomic_ordering)
        existing.update('goals', self.goals)
        return existing

    def has_ability(self, ability):
        for a in self.atomic_ordering:
            if ability.unique == a.unique:
                return True
        return False

    async def which_plugin(self):
        for plugin in os.listdir('plugins'):
            if await self.walk_file_path(os.path.join('plugins', plugin, 'data', ''), '%s.yml' % self.adversary_id):
                return plugin
        return None
