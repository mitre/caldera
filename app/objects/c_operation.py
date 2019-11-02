import asyncio
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
                               source=self.source.display if self.source else '', planner=self.planner.name,
                               state=self.state,
                               start=self.start.strftime('%Y-%m-%d %H:%M:%S'),
                               allow_untrusted=self.allow_untrusted, autonomous=self.autonomous, finish=self.finish,
                               chain=[lnk.display for lnk in self.chain]))

    @property
    def states(self):
        return dict(RUNNING='running',
                    RUN_ONE_LINK='run_one_link',
                    PAUSED='paused',
                    FINISHED='finished')

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
        return existing

    def add_link(self, link):
        link.id = len(self.chain) + 1
        self.chain.append(link)

    def all_facts(self):
        seeded_facts = [f for f in self.source.facts] if self.source else []
        learned_facts = [f for lnk in self.chain for f in lnk.facts if f.score > 0]
        return seeded_facts + learned_facts

    async def apply(self, link):
        while self.state != self.states['RUNNING']:
            if self.state == self.states['RUN_ONE_LINK']:
                self.add_link(link)
                self.state = self.states['PAUSED']
                return link.id
            else:
                await asyncio.sleep(30)
        return self.add_link(link)
