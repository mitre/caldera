from app.utility.base_object import BaseObject


class Parser(BaseObject):

    @property
    def unique(self):
        return self.module

    @property
    def display(self):
        d = dict(module=self.module, relationships=[m.display for m in self.mappers])
        return d

    def __init__(self, module, mappers):
        self.module = module
        self.mappers = mappers
