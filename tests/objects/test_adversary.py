import pytest

from app.objects.c_ability import Ability
from app.objects.c_adversary import Adversary, AdversarySchema


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


class TestAdversaryDictSteps:
    """Tests for adversary atomic_ordering entries that are dicts with embedded metadata."""

    def test_dict_step_adversary_init(self):
        step = {'ability_id': 'abc123', 'metadata': {'executor_facts': {'linux': [{'trait': 'x', 'value': '1'}]}}}
        adv = Adversary(adversary_id='aaa', name='test', description='', atomic_ordering=[step])
        assert adv.atomic_ordering == [step]

    def test_verify_with_dict_steps_warns_missing(self, caplog):
        """verify() should warn about dict steps whose ability_id is not in the ability list."""
        import logging
        step = {'ability_id': 'missing-id', 'metadata': {}}
        adv = Adversary(adversary_id='aaa', name='test', description='',
                        atomic_ordering=[step],
                        objective='495a9828-cab1-44dd-a0ca-66e58177d8cc')
        ability = Ability(ability_id='other-id')
        objective_stub = type('Obj', (), {'id': '495a9828-cab1-44dd-a0ca-66e58177d8cc'})()
        import logging
        log = logging.getLogger('test')
        with caplog.at_level(logging.WARNING, logger='test'):
            adv.verify(log=log, abilities=[ability], objectives=[objective_stub])
        assert any('missing-id' in r.message for r in caplog.records)

    def test_verify_with_dict_steps_no_warning_when_found(self, caplog):
        """verify() should not warn when the ability_id in a dict step exists."""
        import logging
        step = {'ability_id': 'abc123', 'metadata': {}}
        adv = Adversary(adversary_id='aaa', name='test', description='',
                        atomic_ordering=[step],
                        objective='495a9828-cab1-44dd-a0ca-66e58177d8cc')
        ability = Ability(ability_id='abc123')
        objective_stub = type('Obj', (), {'id': '495a9828-cab1-44dd-a0ca-66e58177d8cc'})()
        log = logging.getLogger('test')
        with caplog.at_level(logging.WARNING, logger='test'):
            adv.verify(log=log, abilities=[ability], objectives=[objective_stub])
        assert not any('abc123' in r.message for r in caplog.records)

    def test_check_repeatable_abilities_with_dict_steps(self):
        """check_repeatable_abilities should handle dict-style steps."""
        step = {'ability_id': '456', 'metadata': {}}
        adv = Adversary(adversary_id='aaa', name='test', description='', atomic_ordering=[step])
        repeatable = Ability(ability_id='456', repeatable=True)
        assert adv.check_repeatable_abilities([repeatable])

    def test_check_repeatable_abilities_dict_step_not_repeatable(self):
        step = {'ability_id': '456', 'metadata': {}}
        adv = Adversary(adversary_id='aaa', name='test', description='', atomic_ordering=[step])
        non_repeatable = Ability(ability_id='456', repeatable=False)
        assert not adv.check_repeatable_abilities([non_repeatable])

    def test_schema_load_dict_steps(self):
        """AdversarySchema should accept atomic_ordering entries as dicts."""
        data = {
            'adversary_id': 'test-id',
            'name': 'test',
            'description': '',
            'atomic_ordering': [
                {'ability_id': 'abc', 'metadata': {'executor_facts': {'linux': []}}},
                'plain-id',
            ],
        }
        adv = AdversarySchema().load(data)
        assert isinstance(adv.atomic_ordering[0], dict)
        assert adv.atomic_ordering[0]['ability_id'] == 'abc'
        assert adv.atomic_ordering[1] == 'plain-id'

    def test_schema_roundtrip_dict_steps(self):
        """Dumping an adversary with dict steps and reloading should preserve them."""
        step = {'ability_id': 'abc', 'metadata': {'executor_facts': {'linux': []}}}
        adv = Adversary(adversary_id='test-id', name='test', description='', atomic_ordering=[step])
        dumped = AdversarySchema().dump(adv)
        assert dumped['atomic_ordering'][0] == step
        reloaded = AdversarySchema().load(dumped)
        assert reloaded.atomic_ordering[0] == step

    def test_store_preserves_dict_steps(self, unrepeatable_ability):
        """store() should preserve dict-style steps in RAM."""
        step = {'ability_id': '123', 'metadata': {'executor_facts': {'linux': []}}}
        adv = Adversary(adversary_id='store-test', name='test', description='', atomic_ordering=[step])
        ram = dict(adversaries=[], abilities=[unrepeatable_ability])
        adv.store(ram)
        assert ram['adversaries'][0].atomic_ordering[0] == step
