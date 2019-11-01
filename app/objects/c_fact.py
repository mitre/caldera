from app.objects.base_object import BaseObject


class Fact(BaseObject):

    @property
    def unique(self):
        return self.hash('%s%s' % (self.prop, self.value))

    @property
    def display(self):
        return dict(unique=self.unique, prop=self.prop, value=self.value, score=self.score)

    def __init__(self, prop, value, score=1):
        self.prop = prop
        self.value = value
        self.score = score


