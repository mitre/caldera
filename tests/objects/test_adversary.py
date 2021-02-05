import pytest

from app.objects.c_ability import Ability
from app.objects.c_adversary import Adversary


@pytest.fixture
def unrepeatable_ability():
    return Ability(ability_id='123', repeatable=False)


@pytest.fixture
def repeatable_ability():
    return Ability(ability_id='456', repeatable=True)


class TestAdversary:

    def test_store_not_existing(self, adversary):
        test_adversary = adversary()
        ram = dict(adversaries=[])
        test_adversary.store(ram)
        assert ram == dict(adversaries=[test_adversary])

    def test_store_existing(self, unrepeatable_ability, repeatable_ability):
        test_adversary = Adversary(adversary_id='123', name='test', description='',
                                   atomic_ordering=['123'])
        ram = dict(adversaries=[test_adversary], abilities=[unrepeatable_ability, repeatable_ability])
        test_adversary.atomic_ordering = ['456']
        test_adversary.store(ram)
        assert ram['adversaries'][0].has_repeatable_abilities
        assert ram['adversaries'][0].atomic_ordering[0] == '456'

    def test_check_repeatable_abilities(self, repeatable_ability):
        test_adversary = Adversary(adversary_id='123', name='test', description='',
                                   atomic_ordering=['456'])
        ram = dict(adversaries=[test_adversary], abilities=[repeatable_ability])
        assert test_adversary.check_repeatable_abilities(ram['abilities'])

    def test_update_empty_list(self, adversary, ability):
        test_adversary = adversary()
        test_adversary.atomic_ordering = [ability()]
        test_adversary.update('atomic_ordering', [])
        assert test_adversary.atomic_ordering == []

    def test_update_boolean(self, adversary):
        test_adversary = adversary()
        test_adversary.update('has_repeatable_abilities', False)
        assert not test_adversary.has_repeatable_abilities
