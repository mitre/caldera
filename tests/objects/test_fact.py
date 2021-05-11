from app.objects.secondclass.c_fact import Fact, Restriction, Source, Type


class TestFact:

    def test_escaped_cmd(self):
        test_fact = Fact('test', 'test value| &')
        assert test_fact.escaped('cmd') == 'test^ value^|^ ^&'
        assert test_fact.escaped('cmd') != 'test value| &'

    def test_escaped_sh(self):
        test_fact = Fact('test', 'test value| &')
        test_dupe = test_fact.escaped('sh').replace('\\', '*')
        assert test_dupe == 'test* value*|* *&'
        assert test_fact.escaped('sh') != 'test value| &'

    def test_escaped_psh(self):
        test_fact = Fact('test', 'test value| &')
        assert test_fact.escaped('psh') == 'test` value`|` `&'
        assert test_fact.escaped('psh') != 'test value| &'

    def test_fact_trait_and_name_equals(self):
        test_fact = Fact('test', 'test value')
        assert test_fact.trait == test_fact.name

    def test_fact_trait_change_equals(self):
        expected_value = 'another value'
        test_fact = Fact('test', 'test value')
        test_fact.trait = expected_value
        assert test_fact.name == expected_value
        assert test_fact.trait == expected_value

    def test_fact_name_change_equals(self):
        expected_value = 'another value'
        test_fact = Fact('test', 'test value')
        test_fact.name = expected_value
        assert test_fact.trait == expected_value
        assert test_fact.name == expected_value

    def test_fact_restriction(self):
        test_fact = Fact('test', 'test value', restriction=Restriction.UNIQUE)
        fact_display = test_fact.display
        assert test_fact.restriction == Restriction.UNIQUE
        assert fact_display['restriction'] == 'UNIQUE'

    def test_fact_source(self):
        test_fact = Fact('test', 'test value', source=Source.YAML)
        fact_display = test_fact.display
        assert test_fact.source == Source.YAML
        assert fact_display['source'] == 'YAML'

    def test_fact_type(self):
        test_fact = Fact('test', 'test value', type=Type.DOMAIN)
        fact_display = test_fact.display
        assert test_fact.type == Type.DOMAIN
        assert fact_display['type'] == 'DOMAIN'
