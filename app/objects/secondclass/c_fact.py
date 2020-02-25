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

    @property
    def unique(self):
        return self.hash('%s%s' % (self.trait, self.value))

    @property
    def display(self):
        return dict(unique=self.unique, trait=self.trait, value=self.value, score=self.score, tactic=self.technique_id)

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
