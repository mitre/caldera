import marshmallow as ma

from app.utility.base_object import BaseObject
from app.objects.secondclass.c_fact import FactSchema


class RelationshipSchema(ma.Schema):

    unique = ma.fields.String(dump_only=True)
    source = ma.fields.Nested(FactSchema, required=True)
    edge = ma.fields.String(allow_none=True)
    target = ma.fields.Nested(FactSchema, allow_none=True)
    score = ma.fields.Integer()
    origin = ma.fields.String(allow_none=True)

    @ma.pre_load
    def remove_unique(self, data, **_):
        data.pop('unique', None)
        return data

    @ma.post_load
    def build_relationship(self, data, **kwargs):
        return None if kwargs.get('partial') is True else Relationship(**data)


class RelationshipUpdateSchema(ma.Schema):
    criteria = ma.fields.Nested(RelationshipSchema(partial=True), required=True)
    updates = ma.fields.Nested(RelationshipSchema(partial=True), required=True)


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

    @property
    def flat_display(self):
        temp = self.display
        temp['source'] = temp['source'].display
        if self.target:
            temp['target'] = temp['target'].display
        if self.origin:
            temp['origin'] = self.origin
        return temp

    @property
    def shorthand(self):
        # compute a visual representation of a relationship for recording purposes
        stub = f"{self.source.name}({self.source.value})"
        if self.edge:
            stub += f" : {self.edge}"
            if self.target and self.target.name:
                stub += f" : {self.target.name}({self.target.value})"
        return stub

    def __init__(self, source, edge=None, target=None, score=1, origin=None):
        super().__init__()
        self.source = source
        self.edge = edge
        self.target = target
        self.score = score
        self.origin = origin
