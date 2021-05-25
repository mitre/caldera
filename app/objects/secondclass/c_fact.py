from datetime import datetime
from enum import Enum

import marshmallow as ma
import marshmallow_enum as ma_enum

from app.utility.base_object import BaseObject

escape_ref = {
    'sh': {
        'special': ['\\', ' ', '$', '#', '^', '&', '*', '|', '`', '>',
                    '<', '"', '\'', '[', ']', '{', '}', '?', '~', '%'],
        'escape_prefix': '\\'
    },
    'psh': {
        'special': ['`', '^', '(', ')', '[', ']', '|', '+', '%',
                    '?', '$', '#', '&', '@', '>', '<', '\'', '"', ' '],
        'escape_prefix': '`'
    },
    'cmd': {
        'special': ['^', '&', '<', '>', '|', ' ', '?', '\'', '"'],
        'escape_prefix': '^'
    }
}


class Restriction(Enum):
    UNIQUE = 0
    SINGLE = 1


class OriginType(Enum):
    DOMAIN = 0
    SEEDED = 1
    LEARNED = 2
    IMPORTED = 3


class FactSchema(ma.Schema):

    class Meta:
        unknown = ma.EXCLUDE

    unique = ma.fields.String()
    trait = ma.fields.String()
    name = ma.fields.String()
    value = ma.fields.Function(lambda x: x.value, deserialize=lambda x: str(x), allow_none=True)
    created = ma.fields.DateTime(format='%Y-%m-%d %H:%M:%S')
    score = ma.fields.Integer()
    source = ma.fields.String()
    origin_type = ma_enum.EnumField(OriginType)
    links = ma.fields.List(ma.fields.String())
    relationships = ma.fields.List(ma.fields.String())
    restriction = ma_enum.EnumField(Restriction)
    collected_by = ma.fields.String(allow_none=True)
    technique_id = ma.fields.String(allow_none=True)

    @ma.post_load()
    def build_fact(self, data, **_):
        return Fact(**data)


class Fact(BaseObject):

    schema = FactSchema()
    load_schema = FactSchema(exclude=['unique'])

    @property
    def unique(self):
        return self.hash('%s%s' % (self.trait, self.value))

    @property
    def name(self):
        return self._trait

    @name.setter
    def name(self, value):
        # Keep both values in sync if changed. (backwards compatibility)
        self._trait = value

    @property
    def trait(self):
        return self._trait

    @trait.setter
    def trait(self, value):
        # Keep both values in sync if changed. (backwards compatibility)
        self._trait = value

    def escaped(self, executor):
        if executor not in escape_ref:
            return self.value
        escaped_value = str(self.value)
        for char in escape_ref[executor]['special']:
            escaped_value = escaped_value.replace(char, (escape_ref[executor]['escape_prefix'] + char))
        return escaped_value

    def __eq__(self, other):
        if isinstance(other, Fact):
            return self.unique == other.unique
        return False

    def __init__(self, trait, value=None, score=1, source=None, origin_type=None, links=None,
                 relationships=None, restriction=None, collected_by=None, technique_id=None):
        super().__init__()
        self.trait = trait
        self.value = value
        self.created = datetime.now()
        self.score = score
        self.source = source
        self.origin_type = origin_type
        self.links = links or []
        self.relationships = relationships or []
        self.restriction = restriction
        self.collected_by = collected_by
        self.technique_id = technique_id
