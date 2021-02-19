import os

import marshmallow as ma

from app.objects.interfaces.i_object import FirstClassObjectInterface
from app.utility.base_object import BaseObject


class AdversarySchema(ma.Schema):

    adversary_id = ma.fields.String()
    name = ma.fields.String()
    description = ma.fields.String()
    atomic_ordering = ma.fields.List(ma.fields.String())
    objective = ma.fields.String()
    tags = ma.fields.List(ma.fields.String())
    has_repeatable_abilities = ma.fields.Boolean()

    @ma.pre_load
    def fix_id(self, adversary, **_):
        if 'id' in adversary:
            adversary['adversary_id'] = adversary.pop('id')
        return adversary

    @ma.pre_load
    def phase_to_atomic_ordering(self, adversary, **_):
        """
        Convert legacy adversary phases to atomic ordering
        """
        if 'phases' in adversary and 'atomic_ordering' in adversary:
            raise ma.ValidationError('atomic_ordering and phases cannot be used at the same time', 'phases', adversary)
        elif 'phases' in adversary:
            adversary['atomic_ordering'] = [ab_id for phase in adversary.get('phases', {}).values() for ab_id in phase]
            del adversary['phases']
        return adversary

    @ma.post_load
    def build_adversary(self, data, **_):
        return Adversary(**data)


class Adversary(FirstClassObjectInterface, BaseObject):

    schema = AdversarySchema()

    @property
    def unique(self):
        return self.hash('%s' % self.adversary_id)

    def __init__(self, adversary_id, name, description, atomic_ordering, objective=None, tags=None):
        super().__init__()
        self.adversary_id = adversary_id
        self.name = name
        self.description = description
        self.atomic_ordering = atomic_ordering
        self.objective = objective
        self.tags = set(tags) if tags else set()
        self.has_repeatable_abilities = False

    def store(self, ram):
        existing = self.retrieve(ram['adversaries'], self.unique)
        if not existing:
            ram['adversaries'].append(self)
            return self.retrieve(ram['adversaries'], self.unique)
        existing.update('name', self.name)
        existing.update('description', self.description)
        existing.update('atomic_ordering', self.atomic_ordering)
        existing.update('objective', self.objective)
        existing.update('tags', self.tags)
        existing.update('has_repeatable_abilities', self.check_repeatable_abilities(ram['abilities']))
        return existing

    def has_ability(self, ability):
        for a in self.atomic_ordering:
            if ability == a:
                return True
        return False

    async def which_plugin(self):
        for plugin in os.listdir('plugins'):
            if await self.walk_file_path(os.path.join('plugins', plugin, 'data', ''), '%s.yml' % self.adversary_id):
                return plugin
        return None

    def check_repeatable_abilities(self, ability_list):
        return any(ab.repeatable for ab_id in self.atomic_ordering for ab in ability_list if ab.ability_id == ab_id)
