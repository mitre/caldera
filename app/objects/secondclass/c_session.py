from app.utility.base_object import BaseObject


class Session(BaseObject):

    @property
    def unique(self):
        return self.hash('%s' % self.paw)

    def __init__(self, id, paw, connection):
        super().__init__()
        self.id = id
        self.paw = paw
        self.connection = connection

    def store(self, ram):
        existing = self.retrieve(ram['sessions'], self.unique)
        if not existing:
            ram['sessions'].append(self)
            return self.retrieve(ram['sessions'], self.unique)
        return existing
