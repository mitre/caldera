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
        loop.run_until_complete(knowledge_svc.add_fact(Fact(trait='test', value='demo', score=1,
                                                            collected_by='thin_air', technique_id='T1234')))
        loop.run_until_complete(knowledge_svc.delete_fact(dict(trait='test')))
        facts = loop.run_until_complete(knowledge_svc.get_facts(dict(trait='test')))
        assert len(facts) == 0

    def test_remove_rules(self, loop, knowledge_svc):
        loop.run_until_complete(knowledge_svc.add_rule(Rule(action='BLOCK', trait='a.c', match='.*')))
        loop.run_until_complete(knowledge_svc.delete_rule(dict(trait='a.c')))
        rules = loop.run_until_complete(knowledge_svc.get_rules(dict(trait='a.c')))
        assert len(rules) == 0

    def test_remove_relationship(self, loop, knowledge_svc):
        dummy = Fact(trait='test', value='demo', score=1, collected_by='thin_air', technique_id='T1234')
        loop.run_until_complete(knowledge_svc.add_relationship(Relationship(source=dummy, edge='potato', target=dummy)))
        loop.run_until_complete(knowledge_svc.delete_relationship(dict(edge='potato')))
        relationships = loop.run_until_complete(knowledge_svc.get_relationships(dict(edge='potato')))
        assert len(relationships) == 0

    def test_update_fact(self, loop, knowledge_svc):
        loop.run_until_complete(knowledge_svc.add_fact(Fact(trait='test', value='demo', score=1,
                                                            collected_by='thin_air', technique_id='T1234')))
        loop.run_until_complete(knowledge_svc.update_fact(criteria=dict(trait='test'),updates=dict(trait='test2',
                                                                                                   value='demo2')))
        facts = loop.run_until_complete(knowledge_svc.get_facts(dict(trait='test2')))
        assert len(facts) == 1
        assert facts[0].value == 'demo2'

    def test_update_relationship(self, loop, knowledge_svc):
        dummy = Fact(trait='test', value='demo', score=1, collected_by='thin_air', technique_id='T1234')
        dummy2 = Fact(trait='test2', value='demo2', score=1, collected_by='thin_air', technique_id='T4321')
        loop.run_until_complete(knowledge_svc.add_relationship(Relationship(source=dummy, edge='potato', target=dummy)))
        loop.run_until_complete(knowledge_svc.update_relationship(criteria=dict(edge='potato'),
                                                                  updates=dict(source=dummy2, edge='bacon')))
        relationships = loop.run_until_complete(knowledge_svc.get_relationships(dict(edge='bacon')))
        assert len(relationships) == 1
        assert relationships[0].source == dummy2

    def test_retrieve_fact(self, loop, knowledge_svc):
        loop.run_until_complete(knowledge_svc.add_fact(Fact(trait='testA', value='demoB', score=24,
                                                            collected_by='thin_airA', technique_id='T1234')))
        loop.run_until_complete(knowledge_svc.add_fact(Fact(trait='testB', value='demoA', score=42,
                                                            collected_by='thin_airB', technique_id='T4321')))
        facts = loop.run_until_complete(knowledge_svc.get_facts(dict(trait='testB')))
        assert len(facts) == 1
        readable = facts[0].display
        assert readable['value'] == 'demoA'
        assert readable['score'] == 42

    def test_retrieve_relationship(self, loop, knowledge_svc):
        dummy = Fact(trait='test', value='demo', score=1, collected_by='thin_air', technique_id='T1234')
        dummy2 = Fact(trait='test2', value='demo2', score=1, collected_by='thin_air', technique_id='T1234')
        loop.run_until_complete(knowledge_svc.add_relationship(Relationship(source=dummy, edge='potato',
                                                                            target=dummy2)))
        loop.run_until_complete(knowledge_svc.add_relationship(Relationship(source=dummy2, edge='potato',
                                                                            target=dummy)))
        relationships = loop.run_until_complete(knowledge_svc.get_relationships(dict(edge='potato')))
        assert len(relationships) == 2
        specific = loop.run_until_complete(knowledge_svc.get_relationships(dict(source=dummy)))
        assert len(specific) == 1
        readable = specific[0].display
        assert readable['edge'] == 'potato'
        assert readable['target'].trait == 'test2'

    def test_retrieve_rule(self, loop, knowledge_svc):
        loop.run_until_complete(knowledge_svc.add_rule(Rule(action='BLOCK', trait='a.c', match='1.2.*')))
        loop.run_until_complete(knowledge_svc.add_rule(Rule(action='ALLOW', trait='a.c', match='*.2.*')))
        rules = loop.run_until_complete(knowledge_svc.get_rules(dict(trait='a.c')))
        assert len(rules) == 2

        fuzzy1 = loop.run_until_complete(knowledge_svc.get_rules(dict(match='1.2.3')))
        assert len(fuzzy1) == 2
        fuzzy2 = loop.run_until_complete(knowledge_svc.get_rules(dict(match='3.2.1')))
        assert len(fuzzy2) == 1
        assert fuzzy2[0].action == 'ALLOW'
