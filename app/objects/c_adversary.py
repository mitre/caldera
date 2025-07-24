import uuid

import marshmallow as ma
import logging
logger = logging.getLogger('adversary')
logger.setLevel(logging.DEBUG)

from app.objects.interfaces.i_object import FirstClassObjectInterface
from app.utility.base_object import BaseObject



DEFAULT_OBJECTIVE_ID = '495a9828-cab1-44dd-a0ca-66e58177d8cc'

class AdversarySchema(ma.Schema):

    class Meta:
        unknown = ma.EXCLUDE

    adversary_id = ma.fields.String()
    name = ma.fields.String()
    description = ma.fields.String()
    atomic_ordering = ma.fields.List(
        ma.fields.Raw(),  # Accepts either str or dict — we'll validate in post_load
    )
    objective = ma.fields.String()
    tags = ma.fields.List(ma.fields.String(), allow_none=True)
    has_repeatable_abilities = ma.fields.Boolean(dump_only=True)
    plugin = ma.fields.String(load_default=None)
    metadata = ma.fields.Dict()

    @ma.pre_load
    def fix_id(self, adversary, **_):
        if 'id' in adversary:
            adversary['adversary_id'] = adversary.pop('id')
        return adversary

    @ma.pre_load
    def phase_to_atomic_ordering(self, adversary, **_):
        """
        Convert legacy adversary phases to atomic ordering
        """
        if 'phases' in adversary and 'atomic_ordering' in adversary:
            raise ma.ValidationError('atomic_ordering and phases cannot be used at the same time', 'phases', adversary)
        elif 'phases' in adversary:
            adversary['atomic_ordering'] = [ab_id for phase in adversary.get('phases', {}).values() for ab_id in phase]
            del adversary['phases']
        return adversary

    @ma.pre_load
    def remove_properties(self, data, **_):
        data.pop('has_repeatable_abilities', None)
        return data

    @ma.post_load
    def build_adversary(self, data, **kwargs):
        try:
            atomic_ordering = data.get('atomic_ordering', [])
            metadata = {}

            for idx, step in enumerate(atomic_ordering):
                if isinstance(step, dict):
                    step_metadata = {}

                    if 'facts' in step:
                        step_metadata['facts'] = step['facts']

                    if 'metadata' in step and isinstance(step['metadata'], dict):
                        executor_facts = step['metadata'].get('executor_facts')
                        if executor_facts:
                            step_metadata['executor_facts'] = executor_facts

                    if step_metadata:
                        metadata[str(idx)] = step_metadata

            # Do NOT overwrite atomic_ordering here
            data['metadata'] = data.get('metadata', {})
            data['metadata'].update(metadata)

            return Adversary(**data)
        except Exception as e:
            traceback.print_exc()
            raise

class Adversary(FirstClassObjectInterface, BaseObject):

    schema = AdversarySchema()
    def __new__(cls, *args, **kwargs):
        instance = super().__new__(cls)
        instance.log = logger
        return instance

    @property
    def unique(self):
        return self.hash('%s' % self.adversary_id)

    def __init__(self, name='', adversary_id='', description='', atomic_ordering=(), objective='', tags=None, plugin='', metadata=None, **_):
        super().__init__()
        self.adversary_id = adversary_id if adversary_id else str(uuid.uuid4())
        self.name = name
        self.description = description
        self.atomic_ordering = atomic_ordering
        self.objective = objective or DEFAULT_OBJECTIVE_ID
        self.tags = set(tags) if tags else set()
        self.has_repeatable_abilities = False
        self.plugin = plugin
        self.metadata = metadata or {}
        self.log = logger
        
        
    def store(self, ram):
        existing = self.retrieve(ram['adversaries'], self.unique)
        if not existing:
            ram['adversaries'].append(self)
            return self.retrieve(ram['adversaries'], self.unique)
        existing.update('name', self.name)
        existing.update('description', self.description)
        existing.update('atomic_ordering', self.atomic_ordering)
        existing.update('objective', self.objective)
        existing.update('tags', self.tags)
        existing.update('has_repeatable_abilities', self.check_repeatable_abilities(ram['abilities']))
        existing.update('plugin', self.plugin)
        
        return existing

    def verify(self, log, abilities, objectives):
        if not hasattr(self, 'metadata'):
            self.metadata = {}

        for step in self.atomic_ordering:
            ability_id = step if isinstance(step, str) else step.get('ability_id')
            if not any(ability.ability_id == ability_id for ability in abilities):
                log.warning('Ability referenced in adversary %s but not found: %s',
                            self.adversary_id, ability_id)

        if not self.objective:
            self.objective = DEFAULT_OBJECTIVE_ID
        elif not any(obj.id == self.objective for obj in objectives):
            log.warning('Objective referenced in adversary %s but not found: %s. Setting default objective.',
                        self.adversary_id, self.objective)
            self.objective = DEFAULT_OBJECTIVE_ID

        self.has_repeatable_abilities = self.check_repeatable_abilities(abilities)


    def has_ability(self, ability):
        for a in self.atomic_ordering:
            if ability == a:
                return True
        return False

    async def which_plugin(self):
        return self.plugin

    def check_repeatable_abilities(self, ability_list):
        for step in self.atomic_ordering:
            ability_id = step if isinstance(step, str) else step.get('ability_id')
            for ab in ability_list:
                if ab.ability_id == ability_id and ab.repeatable:
                    return True
        return False