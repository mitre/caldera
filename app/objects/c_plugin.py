import logging
import os
from importlib import import_module

from app.utility.base_object import BaseObject
from app.utility.base_world import BaseWorld


class Plugin(BaseObject):

    @property
    def unique(self):
        return self.hash(self.name)

    @property
    def display(self):
        return self.clean(dict(name=self.name, enabled=self.enabled, address=self.address))

    def __init__(self, name):
        super().__init__()
        self.name = name
        self.description = None
        self.address = None
        self.enabled = False

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
            return True
        except Exception as e:
            logging.error('Error loading plugin=%s, %s' % (self.name, e))
            return True

    async def enable(self, services):
        try:
            optional_secrets = 'plugins/%s/conf/secrets.yml' % self.name.lower()
            if os.path.isfile(optional_secrets):
                services.get('app_svc').config['secrets'][self.name] = BaseWorld.strip_yml(optional_secrets)[0]
            plugin = getattr(self._load_module(), 'enable')
            await plugin(services)
            self.enabled = True
        except Exception as e:
            logging.error('Error enabling plugin=%s, %s' % (self.name, e))

    async def destroy(self):
        destroyable = getattr(self._load_module(), 'destroy', None)
        if destroyable:
            await destroyable()

    """ PRIVATE """

    def _load_module(self):
        try:
            return import_module('plugins.%s.hook' % self.name)
        except Exception as e:
            logging.error('Error importing plugin=%s, %s' % (self.name, e))
