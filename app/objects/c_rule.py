from app.utility.base_object import BaseObject
from app.utility.rule_set import RuleAction


class Rule(BaseObject):
    def __init__(self, action, trait, match='.*'):
        self.action = RuleAction[action]
        self.trait = trait
        self.match = match
