import os

from app.utility.base_object import BaseObject


class Adversary(BaseObject):

    @property
    def unique(self):
        return self.hash('%s' % self.adversary_id)

    @property
    def display(self):
        phases = dict()
        for k, v in self.phases.items():
            phases[k] = [val.display for val in v]
        return dict(adversary_id=self.adversary_id, name=self.name, description=self.description, phases=phases)

    def __init__(self, adversary_id, name, description, phases):
        super().__init__()
        self.adversary_id = adversary_id
        self.name = name
        self.description = description
        self.phases = phases

    def store(self, ram):
        existing = self.retrieve(ram['adversaries'], self.unique)
        if not existing:
            ram['adversaries'].append(self)
            return self.retrieve(ram['adversaries'], self.unique)
        existing.update('name', self.name)
        existing.update('description', self.description)
        existing.update('phases', self.phases)
        return existing

    def has_ability(self, ability):
        for _, v in self.phases.items():
            for a in v:
                if ability.unique == a.unique:
                    return True
        return False

    async def which_plugin(self):
        for plugin in os.listdir('plugins'):
            if await self.walk_file_path(os.path.join('plugins', plugin, 'data', ''), '%s.yml' % self.adversary_id):
                return plugin
        return None
