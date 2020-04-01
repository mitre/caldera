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


class Fact(BaseObject):

    class FactSchema(ma.Schema):
        unique = ma.fields.String()
        trait = ma.fields.String()
        value = ma.fields.String()
        score = ma.fields.Integer()
        technique = ma.fields.String()

        @ma.post_load()
        def build_fact(self, data, **_):
            return Fact(**data)

    @property
    def unique(self):
        return self.hash('%s%s' % (self.trait, self.value))

    @property
    def display(self):
        return self.FactSchema().dump(self)

    def escaped(self, executor):
        if executor not in escape_ref:
            return self.value
        escaped_value = self.value
        for char in escape_ref[executor]['special']:
            escaped_value = escaped_value.replace(char, (escape_ref[executor]['escape_prefix'] + char))
        return escaped_value

    def __init__(self, trait, value, score=1, collected_by=None, technique_id=None):
        super().__init__()
        self.trait = trait
        self.value = value
        self.score = score
        self.collected_by = collected_by
        self.technique_id = technique_id

    @classmethod
    def from_dict(cls, dict_obj):
        return cls(**cls.FactSchema().load(dict_obj))

    @classmethod
    def load(cls, dict_obj):
        return cls.FactSchema().load(dict_obj)
