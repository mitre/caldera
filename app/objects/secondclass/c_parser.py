from app.objects.secondclass.c_parserconfig import ParserConfig
from app.utility.base_object import BaseObject


class Parser(BaseObject):

    @property
    def unique(self):
        return self.module

    @classmethod
    def from_json(cls, json):
        parserconfigs = [ParserConfig.from_json(r) for r in json['relationships']]
        return cls(module=json['module'], parserconfigs=parserconfigs)

    @property
    def display(self):
        return dict(module=self.module, relationships=[p.display for p in self.parserconfigs])

    def __init__(self, module, parserconfigs):
        super().__init__()
        self.module = module
        self.parserconfigs = parserconfigs
