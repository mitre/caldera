from app.objects.secondclass.c_fact import Fact
from app.objects.secondclass.c_relationship import Relationship
from app.objects.secondclass.c_rule import Rule


class TestKnowledgeService:

    def test_no_duplicate_fact(self, loop, knowledge_svc):
        loop.run_until_complete(knowledge_svc.add_fact(Fact(trait='test', value='demo', score=1,
                                                            collected_by='thin_air', technique_id='T1234')))
        loop.run_until_complete(knowledge_svc.add_fact(Fact(trait='test', value='demo', score=1,
                                                            collected_by='thin_air', technique_id='T1234')))
        facts = loop.run_until_complete(knowledge_svc.get_facts(dict(trait='test')))
        assert len(facts) == 1

    def test_no_duplicate_rules(self, loop, knowledge_svc):
        loop.run_until_complete(knowledge_svc.add_rule(Rule(action='BLOCK', trait='a.c', match='.*')))
        loop.run_until_complete(knowledge_svc.add_rule(Rule(action='BLOCK', trait='a.c', match='.*')))
        rules = loop.run_until_complete(knowledge_svc.get_rules(dict(trait='a.c')))
        assert len(rules) == 1

    def test_no_duplicate_relationship(self, loop, knowledge_svc):
        dummy = Fact(trait='test', value='demo', score=1, collected_by='thin_air', technique_id='T1234')
        loop.run_until_complete(knowledge_svc.add_relationship(Relationship(source=dummy, edge='potato', target=dummy)))
        loop.run_until_complete(knowledge_svc.add_relationship(Relationship(source=dummy, edge='potato', target=dummy)))
        relationships = loop.run_until_complete(knowledge_svc.get_relationships(dict(edge='potato')))
        assert len(relationships) == 1

    def test_remove_fact(self, loop, knowledge_svc):
        loop.run_until_complete(knowledge_svc.add_fact(Fact(trait='rtest', value='rdemo', score=1,
                                                            collected_by='thin_air', technique_id='T1234'),
                                                       constraints=dict(test_field='test_value')))
        loop.run_until_complete(knowledge_svc.delete_fact(dict(trait='rtest')))
        facts = loop.run_until_complete(knowledge_svc.get_facts(dict(trait='rtest')))
        assert len(facts) == 0

    def test_remove_rules(self, loop, knowledge_svc):
        loop.run_until_complete(knowledge_svc.add_rule(Rule(action='rBLOCK', trait='ra.c', match='.*'),
                                                       constraints=dict(test_field='test_value')))
        loop.run_until_complete(knowledge_svc.delete_rule(dict(trait='ra.c')))
        rules = loop.run_until_complete(knowledge_svc.get_rules(dict(trait='ra.c')))
        assert len(rules) == 0

    def test_remove_relationship(self, loop, knowledge_svc):
        dummy = Fact(trait='rtest', value='rdemo', score=1, collected_by='thin_air', technique_id='T1234')
        loop.run_until_complete(knowledge_svc.add_relationship(Relationship(source=dummy, edge='rpotato', target=dummy),
                                                               constraints=dict(test_field='test_value')))
        loop.run_until_complete(knowledge_svc.delete_relationship(dict(edge='rpotato')))
        relationships = loop.run_until_complete(knowledge_svc.get_relationships(dict(edge='rpotato')))
        assert len(relationships) == 0

    def test_update_fact(self, loop, knowledge_svc):
        loop.run_until_complete(knowledge_svc.add_fact(Fact(trait='utest', value='udemo', score=1,
                                                            collected_by='thin_air', technique_id='T1234')))
        loop.run_until_complete(knowledge_svc.update_fact(criteria=dict(trait='utest'),
                                                          updates=dict(trait='utest2', value='udemo2')))
        facts = loop.run_until_complete(knowledge_svc.get_facts(dict(trait='utest2')))
        assert len(facts) == 1
        assert facts[0].value == 'udemo2'

    def test_update_relationship(self, loop, knowledge_svc):
        dummy = Fact(trait='utest', value='udemo', score=1, collected_by='thin_air', technique_id='T1234')
        dummy2 = Fact(trait='utest2', value='udemo2', score=1, collected_by='thin_air', technique_id='T4321')
        loop.run_until_complete(knowledge_svc.add_relationship(Relationship(source=dummy, edge='upotato', target=dummy)))
        loop.run_until_complete(knowledge_svc.update_relationship(criteria=dict(edge='upotato'),
                                                                  updates=dict(source=dummy2, edge='ubacon')))
        relationships = loop.run_until_complete(knowledge_svc.get_relationships(dict(edge='ubacon')))
        assert len(relationships) == 1
        assert relationships[0].source == dummy2

    def test_retrieve_fact(self, loop, knowledge_svc):
        loop.run_until_complete(knowledge_svc.add_fact(Fact(trait='ttestA', value='tdemoB', score=24,
                                                            collected_by='thin_airA', technique_id='T1234')))
        loop.run_until_complete(knowledge_svc.add_fact(Fact(trait='ttestB', value='tdemoA', score=42,
                                                            collected_by='thin_airB', technique_id='T4321')))
        facts = loop.run_until_complete(knowledge_svc.get_facts(dict(trait='ttestB')))
        assert len(facts) == 1
        readable = facts[0].display
        assert readable['value'] == 'tdemoA'
        assert readable['score'] == 42

    def test_retrieve_relationship(self, loop, knowledge_svc):
        dummy = Fact(trait='ttest', value='tdemo', score=1, collected_by='thin_air', technique_id='T1234')
        dummy2 = Fact(trait='ttest2', value='tdemo2', score=1, collected_by='thin_air', technique_id='T1234')
        loop.run_until_complete(knowledge_svc.add_relationship(Relationship(source=dummy, edge='tpotato',
                                                                            target=dummy2)))
        loop.run_until_complete(knowledge_svc.add_relationship(Relationship(source=dummy2, edge='tpotato',
                                                                            target=dummy)))
        relationships = loop.run_until_complete(knowledge_svc.get_relationships(dict(edge='tpotato')))
        assert len(relationships) == 2
        specific = loop.run_until_complete(knowledge_svc.get_relationships(dict(source=dummy)))
        assert len(specific) == 1
        readable = specific[0].display
        assert readable['edge'] == 'tpotato'
        assert readable['target'].trait == 'ttest2'

    def test_retrieve_rule(self, loop, knowledge_svc):
        loop.run_until_complete(knowledge_svc.add_rule(Rule(action='tBLOCK', trait='ta.d', match='4.5.*')))
        loop.run_until_complete(knowledge_svc.add_rule(Rule(action='tALLOW', trait='ta.d', match='*.5.*')))
        rules = loop.run_until_complete(knowledge_svc.get_rules(dict(trait='ta.d')))
        assert len(rules) == 2

        fuzzy1 = loop.run_until_complete(knowledge_svc.get_rules(dict(trait='ta.d', match='4.5.6')))
        assert len(fuzzy1) == 2
        fuzzy2 = loop.run_until_complete(knowledge_svc.get_rules(dict(trait='ta.d', match='6.5.4')))
        assert len(fuzzy2) == 1
        assert fuzzy2[0].action == 'tALLOW'
        fuzzy3 = loop.run_until_complete(knowledge_svc.get_rules(dict(trait='ta.d', match='5.*')))
        assert len(fuzzy3) == 2
