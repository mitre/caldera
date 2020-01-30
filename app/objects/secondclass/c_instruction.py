from app.utility.base_object import BaseObject


class Instruction(BaseObject):

    @property
    def display(self):
        return self.clean(dict(id=self.id, sleep=self.sleep, command=self.command, executor=self.executor,
                               timeout=self.timeout, payload=self.payload))

    def __init__(self, link_id, sleep, command, executor, timeout, payload):
        super().__init__()
        self.id = link_id
        self.sleep = sleep
        self.command = command
        self.executor = executor
        self.timeout = timeout
        self.payload = payload
