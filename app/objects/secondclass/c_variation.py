from app.utility.base_object import BaseObject


class Variation(BaseObject):

    @property
    def command(self):
        return self.replace_app_props(self._command)

    @property
    def display(self):
        return self.clean(dict(description=self.description, command=self.command))

    def __init__(self, description, command):
        super().__init__()
        self.description = description
        self._command = self.encode_string(command)

