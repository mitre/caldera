from app.objects.base_object import BaseObject


class Relationship(BaseObject):

    @property
    def unique(self):
        return '%s%s%s%s' % (self.link_id, self.source, self.edge, self.target)

    @property
    def display(self):
        return self.clean(dict(source=self.source, edge=self.edge, target=self.target, link_id=self.link_id))

    def __init__(self, source, edge=None, target=None, link_id=None):
        self.source = source
        self.edge = edge
        self.target = target
        self.link_id = link_id

    def store(self, ram):
        pass
