from app.utility.base_object import BaseObject


class Visibility(BaseObject):

    MIN_SCORE = 1
    MAX_SCORE = 100

    @property
    def display(self):
        return self.clean(dict(score=self.score))

    @property
    def score(self):
        total_score = self._score + sum([a.offset for a in self.adjustments])
        if total_score > self.MAX_SCORE:
            return self.MAX_SCORE
        elif total_score < self.MIN_SCORE:
            return self.MIN_SCORE
        return total_score

    def __init__(self):
        super().__init__()
        self._score = 50
        self.adjustments = []

    def apply(self, adjustment):
        self.adjustments.append(adjustment)
