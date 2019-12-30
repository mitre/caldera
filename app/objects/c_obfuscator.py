import logging
from importlib import import_module

from app.utility.base_object import BaseObject


class Obfuscator(BaseObject):

    @property
    def unique(self):
        return self.hash('%s' % self.name)

    @property
    def display(self):
        return dict(name=self.name, description=self.description)

    def __init__(self, name, description, module):
        super().__init__()
        self.name = name
        self.description = description
        self.module = module

    def store(self, ram):
        existing = self.retrieve(ram['obfuscators'], self.unique)
        if not existing:
            ram['obfuscators'].append(self)
            return self.retrieve(ram['obfuscators'], self.unique)
        return existing

    def load(self, agent):
        try:
            mod = import_module(self.module)
            return getattr(mod, 'Obfuscation')(agent)
        except Exception as e:
            logging.error('Error importing obfuscator=%s, %s' % (self.name, e))
