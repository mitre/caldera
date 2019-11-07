from app.utility.base_object import BaseObject


class Parser(BaseObject):

    @property
    def unique(self):
        return self.module

    @property
    def display(self):
        return self.clean(dict(module=self.module, mappers=[m.display for m in self.mappers]))

    def __init__(self, module, mappers):
        self.module = module
        self.mappers = mappers
