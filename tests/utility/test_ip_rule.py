from app.objects.secondclass.c_fact import Fact
from app.objects.secondclass.c_rule import Rule
from app.utility.rule_set import RuleAction
from app.utility.rule_set import RuleSet


class TestIPRule:
    host1 = "127.0.0.1"
    host2 = "127.0.1.0"
    host3 = "128.0.0.1"
    subnet1 = "127.0.0.0/24"
    fact1 = Fact(trait="host.ip.address", value=host1)
    fact2 = Fact(trait="host.ip.address", value=host2)
    fact3 = Fact(trait="host.ip.address", value=host3)
    rule = Rule(trait="host.ip.address", action=RuleAction.DENY, match=subnet1)
    rs = RuleSet(rules=[rule])

    async def test_is_ip_rule_match(self):
        assert await self.rs._is_ip_rule_match(self.rule, self.fact1)
        assert(not await self.rs._is_ip_rule_match(self.rule, self.fact2))
        assert(not await self.rs._is_ip_rule_match(self.rule, self.fact3))

    async def test_is_fact_allowed(self):
        assert (not await self.rs.is_fact_allowed(self.fact1))
        assert await self.rs.is_fact_allowed(self.fact2)
        assert await self.rs.is_fact_allowed(self.fact3)
