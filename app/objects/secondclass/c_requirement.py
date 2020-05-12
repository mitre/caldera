import marshmallow as ma

from app.objects.secondclass.c_relationship import Relationship
from app.utility.base_object import BaseObject


class RequirementSchema(ma.Schema):

    module = ma.fields.String()
    relationships = ma.fields.Function(lambda obj: [r.display for r in obj.relationships]) # temp - replace with Nested(RelationshipSchema)

    @ma.post_load()
    def build_source(self, data, **_):
        return Requirement(**data)


class Requirement(BaseObject):

    schema = RequirementSchema()

    @property
    def unique(self):
        return self.module

    @classmethod
    def from_json(cls, json):
        relationships = [Relationship.from_json(r) for r in json['relationships']]
        return cls(module=json['module'], relationships=relationships)

    def __init__(self, module, relationships):
        super().__init__()
        self.module = module
        self.relationships = relationships
