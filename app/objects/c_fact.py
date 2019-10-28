from app.objects.base_object import BaseObject


class Fact(BaseObject):

    @property
    def unique(self):
        return self.hash('%s%s%s' % (self.source, self.prop, self.value))

    @property
    def display(self):
        return dict(source=self.source, property=self.prop, value=self.value, score=self.score)

    def __init__(self, source, prop, value, score=1):
        self.prop = prop
        self.value = value
        self.score = score
        self.source = source

    def store(self, ram):
        existing = self.retrieve(ram['facts'], self.unique)
        if not existing:
            ram['facts'].append(self)
            return self.retrieve(ram['facts'], self.unique)

