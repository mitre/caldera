import abc


class EventServiceInterface(abc.ABC):

    @abc.abstractmethod
    def observe_event(self, event, callback):

        """
        Register an event handler
        :param event: The event topic and (optional) subtopic, separated by a '/'
        :param callback: The function that will handle the event
        :return: None
        """
        raise NotImplementedError

    @abc.abstractmethod
    def fire_event(self, event, **callback_kwargs):
        """
        Fire an event
        :param event: The event topic and (optional) subtopic, separated by a '/'
        :param callback_kwargs: Any additional parameters to pass to the event handler
        :return: None
        """
        raise NotImplementedError
