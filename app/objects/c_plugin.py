import logging
import os
from importlib import import_module

import marshmallow as ma

from app.objects.interfaces.i_object import FirstClassObjectInterface
from app.utility.base_object import BaseObject


class PluginSchema(ma.Schema):
    name = ma.fields.String(required=True)
    enabled = ma.fields.Boolean()
    address = ma.fields.String()
    description = ma.fields.String()
    data_dir = ma.fields.String()
    access = ma.fields.Integer()

    @ma.post_load
    def build_plugin(self, data, **kwargs):
        return None if kwargs.get('partial') is True else Plugin(**data)


class Plugin(FirstClassObjectInterface, BaseObject):

    schema = PluginSchema()
    display_schema = PluginSchema(only=['name', 'description', 'enabled', 'address'])

    @property
    def unique(self):
        return self.hash(self.name)

    def __init__(self, name='virtual', description=None, address=None, enabled=False, data_dir=None, access=None):
        super().__init__()
        self.name = name
        self.description = description
        self.address = address
        self.enabled = enabled
        self.data_dir = data_dir
        self.access = access if access else self.Access.APP

    def store(self, ram):
        existing = self.retrieve(ram['plugins'], self.unique)
        if not existing:
            ram['plugins'].append(self)
            return self.retrieve(ram['plugins'], self.unique)
        else:
            existing.update('enabled', self.enabled)
        return existing

    def load_plugin(self):
        try:
            plugin = self._load_module()
            self.description = plugin.description
            self.address = plugin.address
            self.access = getattr(self._load_module(), 'access', self.Access.APP)
            return True
        except Exception as e:
            logging.error('Error loading plugin=%s, %s' % (self.name, e))
            return False

    async def enable(self, services):
        try:
            if os.path.exists('plugins/%s/data' % self.name.lower()):
                self.data_dir = 'plugins/%s/data' % self.name.lower()
            plugin = self._load_module().enable
            await plugin(services)
            self.enabled = True
        except Exception as e:
            logging.error('Error enabling plugin=%s, %s' % (self.name, e))

    async def destroy(self, services):
        if self.enabled:
            destroyable = getattr(self._load_module(), 'destroy', None)
            if destroyable:
                await destroyable(services)

    async def expand(self, services):
        try:
            if self.enabled:
                expansion = getattr(self._load_module(), 'expansion', None)
                if expansion:
                    await expansion(services)
        except Exception as e:
            logging.error('Error expanding plugin=%s, %s' % (self.name, e))

    def _load_module(self):
        try:
            return import_module('plugins.%s.hook' % self.name)
        except Exception as e:
            logging.error('Error importing plugin=%s, %s' % (self.name, e))
