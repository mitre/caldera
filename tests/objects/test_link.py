from app.objects.secondclass.c_link import Link
from app.objects.secondclass.c_fact import Fact


class TestLink:

    def test_link_eq(self, ability):
        test_ability = ability(ability_id='123')
        fact = Fact(trait='remote.host.fqdn', value='dc')
        test_link = Link(command='sc.exe \\dc create sandsvc binpath= "s4ndc4t.exe -originLinkID 111111"',
                         paw='123456', ability=test_ability, id=111111)
        test_link.used = [fact]
        test_link2 = Link(command='sc.exe \\dc create sandsvc binpath= "s4ndc4t.exe -originLinkID 222222"',
                          paw='123456', ability=test_ability, id=222222)
        test_link2.used = [fact]
        assert test_link == test_link2

    def test_link_neq(self, ability):
        test_ability = ability(ability_id='123')
        fact_a = Fact(trait='host.user.name', value='a')
        fact_b = Fact(trait='host.user.name', value='b')
        test_link_a = Link(command='net user a', paw='123456', ability=test_ability, id=111111)
        test_link_a.used = [fact_a]
        test_link_b = Link(command='net user b', paw='123456', ability=test_ability, id=222222)
        test_link_b.used = [fact_b]
        assert test_link_a != test_link_b
