from app.utility.base_object import BaseObject


class Fact(BaseObject):

    @property
    def unique(self):
        return self.hash('%s%s' % (self.trait, self.value))

    @property
    def display(self):
        return dict(unique=self.unique, trait=self.trait, value=self.value, score=self.score)

    def __init__(self, trait, value, score=1, collected_by=None):
        super().__init__()
        self.trait = trait
        self.value = value
        self.score = score
        self.collected_by = collected_by
