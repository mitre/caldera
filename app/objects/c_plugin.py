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
        self.enabled = False
        module = self._load_module()
        self.description = module.description
        self.address = module.address

    def store(self, ram):
        existing = self.retrieve(ram['plugins'], self.unique)
        if not existing:
            ram['plugins'].append(self)
            return self.retrieve(ram['plugins'], self.unique)
        return existing

    async def enable(self, services):
        plugin = getattr(self._load_module(), 'enable')
        await plugin(services)
        self.enabled = True

    """ PRIVATE """

    def _load_module(self):
        try:
            return import_module('plugins.%s.hook' % self.name)
        except Exception as e:
            self.log.error('Failed to import plugin: %s, %s' % (self.name, e))
            exit(1)
