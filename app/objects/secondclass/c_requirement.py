from app.objects.secondclass.c_relationship import Relationship
from app.utility.base_object import BaseObject


class Requirement(BaseObject):

    @property
    def unique(self):
        return self.module

    @classmethod
    def from_json(cls, json):
        relationships = [Relationship.from_json(r) for r in json['relationships']]
        return cls(module=json['module'], relationships=relationships)

    @property
    def display(self):
        return dict(module=self.module, relationships=[r.display for r in self.relationships])

    def __init__(self, module, relationships):
        super().__init__()
        self.module = module
        self.relationships = relationships
