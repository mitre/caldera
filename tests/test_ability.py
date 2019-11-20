from unittest import TestCase
from app.objects.c_ability import Ability
from app.objects.c_parser import Parser
from app.objects.c_relationship import Relationship
from app.objects.c_requirement import Requirement


class TestAbility(TestCase):
    def setUp(self) -> None:
        parsers = [Parser(module='plugins.stockpile.app.parsers.katz',
                          relationships=[Relationship(source=('domain.user.name', 'The Dude'),
                                                      edge='has_password',
                                                      target=('domain.user.pass', 'Lebowski'))])]
        requirements = [Requirement(module='plugins.stockpile.app.parsers.katz',
                                    relationships=[Relationship(source=('domain.user.name', 'The Dude'),
                                                                edge='has_password',
                                                                target=('domain.user.pass', 'Lebowski'))])]
        self.ability = Ability(ability_id='f0d75523-5169-497f-9fae-21082a6fdf1c', tactic='discovery',
                               test='cHMgYXV4', technique_id='T1057', technique='Process Discovery',
                               name='System Processes', description='Identify system processes', cleanup='cHMgYXV4',
                               executor='sh', platform='darwin', payload='test.sh', parsers=parsers,
                               requirements=requirements, privilege='User')

    def test_unique(self):
        self.assertEqual('f0d75523-5169-497f-9fae-21082a6fdf1cdarwinsh', self.ability.unique,
                         msg='Unique ability name is incorrect')

    def test_display(self):
        self.maxDiff = None
        self.assertDictEqual(dict(id='f0d75523-5169-497f-9fae-21082a6fdf1cdarwinsh',
                                  unique='f0d75523-5169-497f-9fae-21082a6fdf1cdarwinsh',
                                  ability_id='f0d75523-5169-497f-9fae-21082a6fdf1c', tactic='discovery',
                                  test='cHMgYXV4', technique_id='T1057', technique_name='Process Discovery',
                                  name='System Processes', description='Identify system processes', cleanup='cHMgYXV4',
                                  executor='sh', platform='darwin', payload='test.sh',
                                  parsers=[dict(module='plugins.stockpile.app.parsers.katz',
                                                relationships=[dict(source=('domain.user.name', 'The Dude'),
                                                                    edge='has_password',
                                                                    target=('domain.user.pass', 'Lebowski'))])],
                                  requirements=[dict(module='plugins.stockpile.app.parsers.katz',
                                                     relationships=[dict(source=('domain.user.name', 'The Dude'),
                                                                         edge='has_password',
                                                                         target=('domain.user.pass', 'Lebowski'))])],
                                  privilege='User'),
                             self.ability.display,
                             msg='Ability display is not exporting correctly')

    def test_store(self):
        pass
