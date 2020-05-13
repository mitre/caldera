import marshmallow as ma

from app.objects.interfaces.i_object import FirstClassObjectInterface
from app.utility.base_object import BaseObject


class ScheduleSchema(ma.Schema):

    name = ma.fields.String()
    schedule = ma.fields.Time()
    task = ma.fields.Function(lambda obj: obj.task.display)


class Schedule(FirstClassObjectInterface, BaseObject):
    schema = ScheduleSchema()

    @property
    def unique(self):
        return self.hash('%s' % self.name)

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
