import uuid

import marshmallow as ma

from app.objects.interfaces.i_object import FirstClassObjectInterface
from app.objects.c_operation import OperationSchema
from app.utility.base_object import BaseObject


class ScheduleSchema(ma.Schema):

    id = ma.fields.String()
    schedule = ma.fields.Time(required=True)
    task = ma.fields.Nested(OperationSchema())

    @ma.post_load
    def build_schedule(self, data, **kwargs):
        return None if kwargs.get('partial') is True else Schedule(**data)


class Schedule(FirstClassObjectInterface, BaseObject):
    schema = ScheduleSchema()

    @property
    def unique(self):
        return self.hash('%s' % self.id)

    def __init__(self, schedule, task, id=''):
        super().__init__()
        self.id = str(id) if id else str(uuid.uuid4())
        self.schedule = schedule
        self.task = task

    def store(self, ram):
        existing = self.retrieve(ram['schedules'], self.unique)
        if not existing:
            ram['schedules'].append(self)
            return self.retrieve(ram['schedules'], self.unique)
        existing.update('schedule', self.schedule)
        existing.task.update('state', self.task.state)
        existing.task.update('autonomous', self.task.autonomous)
        existing.task.update('obfuscator', self.task.obfuscator)
        return existing
