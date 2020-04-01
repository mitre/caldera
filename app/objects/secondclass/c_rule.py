import marshmallow as ma

from app.utility.base_object import BaseObject
from app.utility.rule_set import RuleAction


class Rule(BaseObject):

    class RuleSchema(ma.Schema):
        trait = ma.fields.String()
        match = ma.fields.String()
        action = ma.fields.String()

        @ma.post_load()
        def build_rule(self, data, **_):
            return Rule(**data)

    @property
    def display(self):
        return self.clean(
            self.RuleSchema().dump(self)
        )

    def __init__(self, action, trait, match='.*'):
        super().__init__()
        self.action = RuleAction[action]
        self.trait = trait
        self.match = match

    @classmethod
    def from_dict(cls, dict_obj):
        return cls(**cls.RuleSchema().load(dict_obj))

    @classmethod
    def load(cls, dict_obj):
        return cls.RuleSchema().load(dict_obj)
