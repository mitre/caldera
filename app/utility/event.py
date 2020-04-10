class Observer():
    _observers = {}

    def __init__(self, topic, message=''):
        if topic not in self._observers:
            self._observers[topic] = {'': []}
        if message not in self._observers[topic]:
            self._observers[topic][message] = []

        if message:
            # use '' to observe all events of this topic, regardless of message
            self._observers[topic][''].append(self)
        self._observers[topic][message].append(self)

    @classmethod
    def register(cls, *args, **kwargs):
        return cls(*args, **kwargs)

    def handle(self):
        raise NotImplementedError


class Event():

    def __init__(self, topic, message='', **callback_kwargs):
        for observer in Observer._observers[topic][message]:
            observer.handle(**callback_kwargs)
