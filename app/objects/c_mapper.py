from app.utility.base_object import BaseObject


class Mapper(BaseObject):

    @property
    def unique(self):
        return '%s%s%s%s' % (self.source, self.edge, self.target, self.misc)

    @property
    def display(self):
        return self.clean(dict(source=self.source, edge=self.edge, target=self.target, misc=self.misc))

    def __init__(self, source, edge=None, target=None, misc=None):
        self.source = source
        self.edge = edge
        self.target = target
        self.misc = misc
