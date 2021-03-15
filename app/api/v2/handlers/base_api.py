import abc
import logging

from aiohttp import web


DEFAULT_LOGGER_NAME = "rest_api"


class BaseApi(abc.ABC):
    def __init__(self, logger=None):
        self._logger = logger or self._create_logger()

    @property
    def logger(self):
        return self._logger

    @abc.abstractmethod
    def add_routes(self, app: web.Application):
        pass

    def _create_logger(self):
        return logging.getLogger(DEFAULT_LOGGER_NAME)
