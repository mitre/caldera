from app.utility.base_object import BaseObject


class Executor(BaseObject):

    @property
    def unique(self):
        return self.name

    @property
    def display(self):
        return dict(name=self.name, preferred=self.preferred)

    def __init__(self, name, preferred):
        self.name = name
        self.preferred = preferred

    def store(self, ram):
        existing = self.retrieve(ram['executors'], self.unique)
        if not existing:
            ram['executors'].append(self)
            return self.retrieve(ram['executors'], self.unique)
        return existing
