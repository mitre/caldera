import marshmallow as ma
import marshmallow_enum as ma_enum

from app.utility.base_object import BaseObject
from app.utility.rule_set import RuleAction


class RuleSchema(ma.Schema):

    action = ma_enum.EnumField(RuleAction, required=True)
    trait = ma.fields.String(required=True)
    match = ma.fields.String()

    @ma.post_load
    def build_rule(self, data, **_):
        return Rule(**data)


class Rule(BaseObject):

    schema = RuleSchema()

    def __init__(self, action, trait, match='.*'):
        super().__init__()
        self.action = action
        self.trait = trait
        self.match = match
