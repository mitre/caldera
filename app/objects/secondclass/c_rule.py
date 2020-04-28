import marshmallow as ma

from app.utility.base_object import BaseObject
from app.utility.rule_set import RuleAction


class RuleActionField(ma.fields.Field):
    """
    Custom field to handle the RuleAction Enum.
    """

    def _serialize(self, value, attr, obj, **kwargs):
        if value is None:
            return None
        return value.value

    def _deserialize(self, value, attr, data, **kwargs):
        return RuleAction[value]


class RuleSchema(ma.Schema):

    trait = ma.fields.String()
    match = ma.fields.String()
    action = RuleActionField()

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
