from app.objects.c_ability import Ability
from app.objects.c_operation import Operation
from app.objects.secondclass.c_fact import Fact
from app.objects.secondclass.c_link import Link
from app.utility.base_world import BaseWorld
from tests.base.test_base import TestBase


class TestLearningSvc(TestBase):

    def setUp(self):
        self.initialize()
        self.ability = self.run_async(self.data_svc.store(
            Ability(ability_id='123', tactic='discovery', technique_id='T1033', technique='Find', name='test',
                    test='d2hvYW1pCg==', description='find active user', cleanup='', executor='sh',
                    platform='darwin', payload='wifi.sh', parsers=[], requirements=[], privilege=None)
        ))
        self.operation = Operation(name='sample', agents=None, adversary=None)
        self.run_async(self.data_svc.store(self.operation))

    def test_learn(self):
        link = Link(operation=self.operation.id, ability=self.ability, command=None, paw=None)
        self.operation.add_link(link)
        self.run_async(self.learning_svc.learn(
            link=link,
            blob=BaseWorld.encode_string('i contain 1 ip address 192.168.0.1 and one file /etc/host.txt. that is all.'))
        )
        self.assertEqual(2, len(link.facts))

    def test_build_relationships(self):
        self.learning_svc.model.add(frozenset({'host.user.name', 'target.org.name'}))
        self.learning_svc.model.add(frozenset({'host.file.extension', 'host.user.name', 'domain.user.name'}))
        facts = [
            Fact(trait='target.org.name', value='something'),
            Fact(trait='host.user.name', value='admin'),
            Fact(trait='host.user.name', value='root'),
            Fact(trait='domain.user.name', value='user'),
            Fact(trait='not.really.here', value='should never be found')
        ]
        link = Link(operation=self.operation.id, ability=self.ability, command=None, paw=None)
        self.run_async(self.learning_svc._build_relationships(link, facts))
        self.assertEqual(4, len(link.relationships))
