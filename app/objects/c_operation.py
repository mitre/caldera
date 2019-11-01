from datetime import datetime

from app.objects.base_object import BaseObject


class Operation(BaseObject):

    @property
    def unique(self):
        return self.name

    @property
    def display(self):
        return self.clean(dict(name=self.name, host_group=[a.display for a in self.agents],
                               adversary=self.adversary.display, jitter=self.jitter,
                               source=self.source.display if self.source else '', planner=self.planner.name, state=self.state,
                               start=self.start.strftime('%Y-%m-%d %H:%M:%S'),
                               allow_untrusted=self.allow_untrusted, autonomous=self.autonomous, finish=self.finish,
                               chain=[lnk.display for lnk in self.chain]))

    def __init__(self, name, agents, adversary, jitter='2/8', source=None, planner=None, state=None,
                 allow_untrusted=False, autonomous=True):
        self.name = name
        self.agents = agents
        self.adversary = adversary
        self.jitter = jitter
        self.source = source
        self.planner = planner
        self.state = state
        self.allow_untrusted = allow_untrusted
        self.autonomous = autonomous
        self.phase = 0
        self.start = datetime.now()
        self.finish = None
        self.chain = []
        self.rules = []

    def store(self, ram):
        existing = self.retrieve(ram['operations'], self.unique)
        if not existing:
            ram['operations'].append(self)
            return self.retrieve(ram['operations'], self.unique)

    def all_facts(self):
        seeded_facts = [f for f in self.source.facts] if self.source else []
        learned_facts = [f for lnk in self.chain for f in lnk.facts if f.score > 0]
        return seeded_facts + learned_facts
