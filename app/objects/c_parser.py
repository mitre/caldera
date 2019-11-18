from app.utility.base_object import BaseObject


class Parser(BaseObject):

    @property
    def unique(self):
        return self.module

    @property
    def display(self):
        return dict(module=self.module, relationships=[p.display for p in self.parserconfigs])

    def __init__(self, module, parserconfigs):
        self.module = module
        self.parserconfigs = parserconfigs
