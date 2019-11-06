from app.utility.base_object import BaseObject


class Parser(BaseObject):

    @property
    def unique(self):
        return self.module

    @property
    def display(self):
        print('c_parser.py 1')
        d = dict(module=self.module, relationships=[m.display for m in self.mappers])
        print('c_parser.py 2')
        return d

    def __init__(self, module, mappers):
        self.module = module
        self.mappers = mappers
