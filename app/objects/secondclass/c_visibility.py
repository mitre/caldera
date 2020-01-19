from collections import namedtuple

from app.utility.base_object import BaseObject


Adjustment = namedtuple('Adjustment', 'trait value score')


class Visibility(BaseObject):

    @property
    def adjustments(self):
        return self._adjustments

    @adjustments.setter
    def adjustments(self, a):
        self._adjustments = [Adjustment(k, adj.get('value'), adj.get('score')) for k, v in a.items() for adj in v]

    def __init__(self, score=50):
        super().__init__()
        self.score = int(score)
        self._adjustments = []
