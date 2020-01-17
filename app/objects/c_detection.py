from app.utility.base_object import BaseObject


class Detection(BaseObject):

    def __init__(self, visibility, adjustments):
        super().__init__()
        self.visibility = visibility
        self.adjustments = adjustments

