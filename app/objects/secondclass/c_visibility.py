from collections import namedtuple

from app.utility.base_object import BaseObject


Adjustment = namedtuple('Adjustment', 'trait value offset')


class Visibility(BaseObject):

    def __init__(self, score=50, adjustments=()):
        super().__init__()
        self.score = score
        self.adjustments = [Adjustment(k, v.get('value'), v.get('offset')) for a in adjustments for k, v in a.items()]
