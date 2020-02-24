from app.objects.c_ability import Ability
from app.objects.c_operation import Operation
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
