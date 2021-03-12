import abc
import logging


class BaseApi(abc.ABC):
    def __init__(self, logger=None):
        self._logger = logger or self._create_logger()

    @property
    def logger(self):
        return self._logger

    @abc.abstractmethod
    def add_routes(self, app):
        pass

    def _create_logger(self):
        """"""
        logger_name = f"{self.__module__}.{self.__class__.__name__}"
        return logging.getLogger(logger_name)
