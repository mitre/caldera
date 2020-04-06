class Observer():
    _observers = []

    def __init__(self):
        self._observers.append(self)
        self._observed_events = []

    def observe(self, event_name, callback_fn):
        self._observed_events.append({'name': event_name, 'callback': callback_fn})


class Event():

    def __init__(self, event_name, *callback_args):
        for observer in Observer._observers:
            for event in observer._observed_events:
                if event['name'] == event_name:
                    event['callback'](*callback_args)
