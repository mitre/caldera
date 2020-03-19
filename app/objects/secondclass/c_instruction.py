from app.utility.base_object import BaseObject


class Instruction(BaseObject):

    @property
    def display(self):
        return self.clean(dict(id=self.id, sleep=self.sleep, command=self.command, executor=self.executor,
                               timeout=self.timeout, payload=self.payload))

    def __init__(self, identifier, command, executor, payload=None, sleep=0, timeout=60):
        super().__init__()
        self.id = identifier
        self.sleep = sleep
        self.command = command
        self.executor = executor
        self.timeout = timeout
        self.payload = payload
