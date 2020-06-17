import marshmallow as ma

from app.utility.base_object import BaseObject
from app.objects.secondclass.c_fact import FactSchema


class RelationshipSchema(ma.Schema):

    unique = ma.fields.String()
    source = ma.fields.Nested(FactSchema())
    edge = ma.fields.String()
    target = ma.fields.Nested(FactSchema())
    score = ma.fields.Integer()

    @ma.post_load
    def build_relationship(self, data, **_):
        return Relationship(**data)


class Relationship(BaseObject):

    schema = RelationshipSchema()
    load_schema = RelationshipSchema(exclude=['unique'])

    @property
    def unique(self):
        return '%s%s%s' % (self.source, self.edge, self.target)

    @classmethod
    def from_json(cls, json):
        return cls(source=json['source'], edge=json.get('edge'), target=json.get('target'), score=json.get('score'))

    @property
    def display(self):
        return self.clean(dict(source=self.source, edge=self.edge,
                               target=[self.target if self.target else 'Not Used'][0], score=self.score))

    def __init__(self, source, edge=None, target=None, score=1):
        super().__init__()
        self.source = source
        self.edge = edge
        self.target = target
        self.score = score
