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
        return dict(adversary_id=self.adversary_id, name=self.name, description=self.description, phases=phases, is_pack=self.is_pack)

    def __init__(self, adversary_id, name, description, phases, is_pack):
        super().__init__()
        self.adversary_id = adversary_id
        self.name = name
        self.description = description
        self.phases = phases
        self.is_pack = is_pack

    def store(self, ram):
        key = 'packs' if self.is_pack else 'adversaries'
        existing = self.retrieve(ram[key], self.unique)
        if not existing:
            ram[key].append(self)
            return self.retrieve(ram[key], self.unique)
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
