from app.utility.base_object import BaseObject


class Detector(BaseObject):

    @property
    def unique(self):
        return self.hash('%s' % self.detector_id)

    @property
    def display(self):
        return dict(detector_id=self.detector_id, event_id=self.event_id, description=self.description)

    def __init__(self, detector_id, event_id, description):
        super().__init__()
        self.detector_id = detector_id
        self.event_id = event_id
        self.description = description

    def store(self, ram):
        existing = self.retrieve(ram['detectors'], self.unique)
        if not existing:
            ram['detectors'].append(self)
            return self.retrieve(ram['detectors'], self.unique)
        existing.update('event_id', self.event_id)
        existing.update('description', self.description)
        return existing
