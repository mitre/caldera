import logging
import os
from importlib import import_module

from app.utility.base_object import BaseObject


class Plugin(BaseObject):

    @property
    def unique(self):
        return self.hash(self.name)

    @property
    def display(self):
        return self.clean(dict(name=self.name, enabled=self.enabled, address=self.address))

    def __init__(self, name='virtual', description=None, address=None, enabled=False, data_dir=None, access=None):
        super().__init__()
        self.name = name
        self.description = description
        self.address = address
        self.enabled = enabled
        self.data_dir = data_dir
        self.access = access if access else self.Access.APP
        self.version = None

    def store(self, ram):
        existing = self.retrieve(ram['plugins'], self.unique)
        if not existing:
            ram['plugins'].append(self)
            return self.retrieve(ram['plugins'], self.unique)
        else:
            existing.update('enabled', self.enabled)
        return existing

    async def load(self):
        try:
            plugin = self._load_module()
            self.description = plugin.description
            self.address = plugin.address
            self.access = getattr(self._load_module(), 'access', self.Access.APP)
            return True
        except Exception as e:
            logging.error('Error loading plugin=%s, %s' % (self.name, e))
            return True

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

    """ PRIVATE """

    def _load_module(self):
        try:
            return import_module('plugins.%s.hook' % self.name)
        except Exception as e:
            logging.error('Error importing plugin=%s, %s' % (self.name, e))
