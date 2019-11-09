from app.utility.base_object import BaseObject


class C2(BaseObject):
    @property
    def unique(self):
        return '%s%s' % (self.module, self.config)

    @property
    def display(self):
        return dict(module=self.module, config=self.config)

    def __init__(self, c2_type, name='http', module=None, config={}):
        self.name = name
        self.module = module
        self.config = config
        self.c2_type = c2_type

    def store(self, ram):
        existing = self.retrieve(ram['c2'], self.unique)
        if not existing:
            ram['c2'].append(self)
            return self.retrieve(ram['c2'], self.unique)
        return existing
