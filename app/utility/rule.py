import re
from enum import Enum


class RuleAction(Enum):
    ALLOW = 1
    DENY = 0


class RuleSet:
    def __init__(self, rules):
        self.rules = rules

    async def is_fact_allowed(self, fact):
        allowed = True
        for rule in self.rules.get(fact['property'], []):
            if re.match(rule.get('match', '.*'), fact['value']):
                if rule['action'] == RuleAction.DENY.value:
                    allowed = False
                elif rule['action'] == RuleAction.ALLOW.value:
                    allowed = True
        return allowed

    async def apply_rules(self, facts):
        if await self._has_rules():
            valid_facts = []
            for fact in facts:
                if await self.is_fact_allowed(fact):
                    valid_facts.append(fact)
            return [valid_facts]
        else:
            return [facts]

    async def _has_rules(self):
        return len(self.rules)

