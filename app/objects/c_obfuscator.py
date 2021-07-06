import logging
from importlib import import_module

import marshmallow as ma

from app.objects.interfaces.i_object import FirstClassObjectInterface
from app.utility.base_object import BaseObject


class ObfuscatorSchema(ma.Schema):

    name = ma.fields.String()
    description = ma.fields.String()
    module = ma.fields.String()

    @ma.post_load
    def build_obfuscator(self, data, **kwargs):
        return None if kwargs.get('partial') is True else Obfuscator(**data)


class Obfuscator(FirstClassObjectInterface, BaseObject):
    schema = ObfuscatorSchema()
    display_schema = ObfuscatorSchema(exclude=['module'])

    @property
    def unique(self):
        return self.hash('%s' % self.name)

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
            return mod.Obfuscation(agent)
        except Exception as e:
            logging.error('Error importing obfuscator=%s, %s' % (self.name, e))
