from app.utility.base_object import BaseObject


class Relationship(BaseObject):

    @property
    def unique(self):
        return '%s%s%s' % (self.source, self.edge, self.target)

    @classmethod
    def from_json(cls, json):
        return cls(source=json['source'], edge=json.get('edge'), target=json.get('target'), score=json.get('score'))

    @property
    def display(self):
        return self.clean(dict(source=self.source, edge=self.edge, target=self.target, score=self.score))

    def __init__(self, source, edge=None, target=None, score=1):
        super().__init__()
        self.source = source
        self.edge = edge
        self.target = target
        self.score = score
