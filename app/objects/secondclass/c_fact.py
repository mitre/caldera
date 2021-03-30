import marshmallow as ma

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


class FactSchema(ma.Schema):

    class Meta:
        unknown = ma.EXCLUDE

    unique = ma.fields.String()
    trait = ma.fields.String()
    value = ma.fields.Function(lambda x: x.value, deserialize=lambda x: str(x), allow_none=True)
    score = ma.fields.Integer()
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

    def __init__(self, trait, value=None, score=1, collected_by=None, technique_id=None):
        super().__init__()
        self.trait = trait
        self.value = value
        self.score = score
        self.collected_by = collected_by
        self.technique_id = technique_id
