from app.utility.base_object import BaseObject


class Source(BaseObject):

    @property
    def unique(self):
        return self.hash('%s' % self.name)

    @property
    def display(self):
        return dict(name=self.name, facts=[f.display for f in self.get_facts()])

    def get_facts(self):
        return [fact for fact_set in self.facts.values() for fact in fact_set]

    def __init__(self, name, facts):
        self.name = name
        self.facts = facts

    def store(self, ram):
        existing = self.retrieve(ram['sources'], self.unique)
        if not existing:
            ram['sources'].append(self)
            return self.retrieve(ram['sources'], self.unique)
        return existing

