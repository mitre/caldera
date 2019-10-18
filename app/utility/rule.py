import re
from enum import Enum
import ipaddress


class RuleAction(Enum):
    ALLOW = 1
    DENY = 0


class RuleSet:
    def __init__(self, rules):
        self.rules = rules

    async def is_fact_allowed(self, fact):
        allowed = True
        for rule in self.rules.get(fact['property'], []):
            if await self._is_ip_rule_match(rule, fact):
                allowed = await self._rule_judgement(rule['action'])
                continue

            if await self._is_regex_rule_match(rule, fact):
                allowed = await self._rule_judgement(rule['action'])
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

    @staticmethod
    async def _rule_judgement(action):
        if action == RuleAction.DENY.value:
            return False
        return True

    @staticmethod
    async def _is_ip_network(value):
        try:
            ipaddress.IPv4Network(value)
            return True
        except (ValueError, ipaddress.AddressValueError):
            pass
        return False

    @staticmethod
    async def _is_regex_rule_match(rule, fact):
        return re.match(rule.get('match', '.*'), fact['value'])

    async def _is_ip_rule_match(self, rule, fact):
        if rule['match'] != '.*' and await self._is_ip_network(rule['match']) and await self._is_ip_network(fact['value']):
            if ipaddress.IPv4Network(fact['value']).subnet_of(ipaddress.IPv4Network(rule['match'])):
                return True
        return False
