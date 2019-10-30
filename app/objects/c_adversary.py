from app.objects.base_object import BaseObject


class Adversary(BaseObject):

    @property
    def unique(self):
        return self.hash('%s' % self.adversary_id)

    @property
    def display(self):
        phases = dict()
        for k,v in self.phases.items():
            phases[k] = [val.display for val in v]
        return dict(adversary_id=self.adversary_id, name=self.name, description=self.description,
                    phases=phases)

    def __init__(self, adversary_id, name, description, phases):
        self.adversary_id = adversary_id
        self.name = name
        self.description = description
        self.phases = phases

    def store(self, ram):
        existing = self.retrieve(ram['adversaries'], self.unique)
        if not existing:
            ram['adversaries'].append(self)
            return self.retrieve(ram['adversaries'], self.unique)
