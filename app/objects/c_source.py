from app.utility.base_object import BaseObject


class Source(BaseObject):

    @property
    def unique(self):
        return self.hash('%s' % self.name)

    @property
    def display(self):
        return dict(name=self.name, facts=[f.display for f in self.facts])

    def __init__(self, name, facts, rules=None):
        super().__init__()
        self.name = name
        self.facts = facts
        self.rules = rules or []

    def store(self, ram):
        existing = self.retrieve(ram['sources'], self.unique)
        if not existing:
            ram['sources'].append(self)
            return self.retrieve(ram['sources'], self.unique)
        return existing
