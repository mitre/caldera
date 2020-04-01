import marshmallow as ma

from app.utility.base_object import BaseObject
from app.utility.rule_set import RuleAction


class RuleSchema(ma.Schema):
    trait = ma.fields.String()
    match = ma.fields.String()
    action = ma.fields.String()

    @ma.post_load()
    def build_rule(self, data, **_):
        return Rule(**data)


class Rule(BaseObject):

    schema = RuleSchema()

    def __init__(self, action, trait, match='.*'):
        super().__init__()
        self.action = RuleAction[action]
        self.trait = trait
        self.match = match
