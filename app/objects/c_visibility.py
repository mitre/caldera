from app.utility.base_object import BaseObject


class Visibility(BaseObject):

    def __init__(self, score, adjustments=()):
        super().__init__()
        self.score = score
        self.adjustments = adjustments

