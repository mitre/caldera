from app.utility.base_object import BaseObject


class Mapper(BaseObject):

    @property
    def unique(self):
        return '%s%s%s%s' % (self.source, self.edge, self.target, self.json_key)

    @property
    def display(self):
        return self.clean(dict(source=self.source, edge=self.edge, target=self.target, json_key=self.json_key))

    def __init__(self, source, edge=None, target=None, json_key=None):
        self.source = source
        self.edge = edge
        self.target = target
        self.json_key = json_key
