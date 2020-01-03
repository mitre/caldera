from app.utility.base_object import BaseObject


class Schedule(BaseObject):

    @property
    def unique(self):
        return self.hash('%s' % self.name)

    @property
    def display(self):
        return dict()

    def __init__(self, name, schedule, task):
        super().__init__()
        self.name = name
        self.schedule = schedule
        self.task = task

    def store(self, ram):
        existing = self.retrieve(ram['schedules'], self.unique)
        if not existing:
            ram['schedules'].append(self)
            return self.retrieve(ram['schedules'], self.unique)
        return existing
