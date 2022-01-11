from datetime import datetime, timezone
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


class OriginType(Enum):
    DOMAIN = 0
    SEEDED = 1
    LEARNED = 2
    IMPORTED = 3
    USER = 4


WILDCARD_STRING = '[USER INPUT THIS UNBOUNDED FACT/RELATIONSHIP]'


class FactSchema(ma.Schema):

    class Meta:
        unknown = ma.EXCLUDE

    unique = ma.fields.String(dump_only=True)
    trait = ma.fields.String(required=True)
    name = ma.fields.String(dump_only=True)
    value = ma.fields.Function(lambda x: x.value, deserialize=lambda x: str(x), allow_none=True)
    created = ma.fields.DateTime(format=BaseObject.TIME_FORMAT, dump_only=True)
    score = ma.fields.Integer()
    source = ma.fields.String(allow_none=True)
    origin_type = ma_enum.EnumField(OriginType, allow_none=True)
    links = ma.fields.List(ma.fields.String())
    relationships = ma.fields.List(ma.fields.String())
    limit_count = ma.fields.Integer()
    collected_by = ma.fields.List(ma.fields.String())
    technique_id = ma.fields.String(allow_none=True)

    @ma.post_load()
    def build_fact(self, data, **kwargs):
        return None if kwargs.get('partial') is True else Fact(**data)


class FactUpdateRequestSchema(ma.Schema):
    criteria = ma.fields.Nested(FactSchema(partial=True), required=True)
    updates = ma.fields.Nested(FactSchema(partial=True), required=True)


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
            return self.unique == other.unique and self.source == other.source
        return False

    def __init__(self, trait, value=None, score=1, source=None, origin_type=None, links=None,
                 relationships=None, limit_count=-1, collected_by=None, technique_id=None):
        super().__init__()
        self.trait = trait
        self.value = value
        self.created = datetime.now(timezone.utc)
        self.score = score
        self.source = source
        self.origin_type = origin_type
        self.links = links or []
        self.relationships = relationships or []
        self.limit_count = limit_count
        self.collected_by = collected_by or []
        self.technique_id = technique_id
