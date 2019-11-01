from app.objects.base_object import BaseObject


class Relationship(BaseObject):

    @property
    def unique(self):
        return '%s%s%s' % (self.source, self.edge, self.target)

    @property
    def display(self):
        return self.clean(dict(source=self.source, edge=self.edge, target=self.target))

    def __init__(self, source, edge=None, target=None):
        self.source = source
        self.edge = edge
        self.target = target

    def store(self, ram):
        pass
