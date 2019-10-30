from app.objects.base_object import BaseObject


class Operation(BaseObject):

    @property
    def unique(self):
        return self.name

    def display(self):
        return dict(name=self.name)

    def __init__(self, name, agents, adversary, jitter='2/8', sources=[], planner=None, state=None,
                 allow_untrusted=False, autonomous=True):
        self.name = name
        self.agents = agents
        self.adversary = adversary
        self.jitter = jitter
        self.sources = sources
        self.planner = planner
        self.state = state
        self.allow_untrusted = allow_untrusted
        self.autonomous = autonomous

    def store(self, ram):
        pass
