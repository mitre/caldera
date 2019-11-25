from importlib import import_module

from app.utility.base_object import BaseObject


class Plugin(BaseObject):

    @property
    def unique(self):
        return self.hash(self.name)

    @property
    def display(self):
        return dict(name=self.name, enabled=self.enabled)

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
        return existing

    async def load(self):
        try:
            plugin = self._load_module()
            self.description = plugin.description
            self.address = plugin.address
            return True
        except Exception:
            self.log.error('Error loading plugin=%s' % self.name)
            return True

    async def enable(self, services):
        try:
            plugin = getattr(self._load_module(), 'enable')
            await plugin(services)
            self.enabled = True
        except Exception:
            self.log.error('Error enabling plugin=%s' % self.name)

    """ PRIVATE """

    def _load_module(self):
        try:
            return import_module('plugins.%s.hook' % self.name)
        except Exception:
            self.log.error('Error importing plugin=%s' % self.name)
            exit(1)
