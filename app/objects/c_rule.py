from app.utility.base_object import BaseObject
from app.utility.rule_set import RuleAction


class Rule(BaseObject):

    @property
    def display(self):
        return self.clean(dict(trait=self.trait, match=self.match, action=self.action.value))

    def __init__(self, action, trait, match='.*'):
        super().__init__()
        self.action = RuleAction[action]
        self.trait = trait
        self.match = match
