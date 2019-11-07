from app.utility.base_object import BaseObject


class Ability(BaseObject):

    @property
    def unique(self):
        return '%s%s%s' % (self.ability_id, self.platform, self.executor)

    @property
    def display(self):
        return self.clean(dict(id=self.unique, ability_id=self.ability_id, tactic=self.tactic,
                               technique_name=self.technique_name,
                               technique_id=self.technique_id, name=self.name,
                               test=self.test, description=self.description, cleanup=self.cleanup,
                               executor=self.executor, unique=self.unique,
                               platform=self.platform, payload=self.payload, parsers=[p.display for p in self.parsers],
                               requirements=[r.display for r in self.requirements], privilege=self.privilege))

    def __init__(self, ability_id, tactic, technique_id, technique, name, test, description, cleanup, executor,
                 platform, payload, parsers, requirements, privilege):
        self.ability_id = ability_id
        self.tactic = tactic
        self.technique_name = technique
        self.technique_id = technique_id
        self.name = name
        self.test = test
        self.description = description
        self.cleanup = cleanup
        self.executor = executor
        self.platform = platform
        self.payload = payload
        self.parsers = parsers
        self.requirements = requirements
        self.privilege = privilege

    def store(self, ram):
        existing = self.retrieve(ram['abilities'], self.unique)
        if not existing:
            ram['abilities'].append(self)
            return self.retrieve(ram['abilities'], self.unique)
        return existing
