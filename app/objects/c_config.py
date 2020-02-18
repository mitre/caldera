from app.utility.base_object import BaseObject


class Config(BaseObject):

    @property
    def unique(self):
        return self.hash('%s' % self.name)

    def __init__(self, name, contents):
        super().__init__()
        self.name = name
        self.contents = contents

    def store(self, ram):
        existing = self.retrieve(ram['configs'], self.unique)
        if not existing:
            ram['configs'].append(self)
            return self.retrieve(ram['configs'], self.unique)
        return existing
