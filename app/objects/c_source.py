from app.utility.base_object import BaseObject


class Source(BaseObject):

    @property
    def unique(self):
        return self.hash('%s' % self.id)

    @property
    def display(self):
        return self.clean(
            dict(id=self.id, name=self.name, facts=[f.display for f in self.facts], rules=[r.display for r in self.rules])
        )

    def __init__(self, identifier, name, facts, rules=(), adjustments=()):
        super().__init__()
        self.id = identifier
        self.name = name
        self.facts = facts
        self.rules = rules
        self.adjustments = adjustments

    def store(self, ram):
        existing = self.retrieve(ram['sources'], self.unique)
        if not existing:
            ram['sources'].append(self)
            return self.retrieve(ram['sources'], self.unique)
        existing.update('name', self.name)
        existing.update('facts', self.facts)
        existing.update('rules', self.rules)
        return existing
