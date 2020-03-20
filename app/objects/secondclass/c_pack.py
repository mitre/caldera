from app.utility.base_object import BaseObject


class Pack(BaseObject):

    @property
    def unique(self):
        return self.name

    @property
    def display(self):
        return dict(name=self.name, atomic_ordering=self.atomic_ordering)

    def __init__(self, name, atomic_ordering):
        super().__init__()
        self.name = name
        self.atomic_ordering = atomic_ordering
