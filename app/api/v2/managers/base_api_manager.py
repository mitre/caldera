import logging
from typing import List


DEFAULT_LOGGER_NAME = 'rest_api_manager'


class BaseApiManager:
    def __init__(self, data_svc, logger=None):
        self._data_svc = data_svc
        self._log = logger or self._create_default_logger()

    @property
    def log(self):
        return self._log

    def get_objects_with_filters(self, object_name: str, search: dict = None, sort: str = None, include: List[str] = None,
                                 exclude: List[str] = None):
        objs = [self.dump_with_include_exclude(obj, include, exclude) for obj in self._data_svc.ram[object_name]
                if not search or obj.match(search)]
        return sorted(objs, key=lambda p: p.get(sort, 0))

    def get_object_with_filters(self, object_name: str, search: dict = None, include: List[str] = None,
                                exclude: List[str] = None):
        for obj in self._data_svc.ram[object_name]:
            if not search or obj.match(search):
                return self.dump_with_include_exclude(obj, include, exclude)

    def delete_object(self, object_name: str, search: dict = None):
        for obj in self._data_svc.ram[object_name]:
            if not search or obj.match(search):
                data = self._data_svc.ram[object_name].copy()
                data.remove(obj)
                self._data_svc.ram[object_name] = data

    def update_object(self, object_name: str, parameters: dict):
        pass

    @staticmethod
    def dump_with_include_exclude(obj, include: List[str] = None, exclude: List[str] = None):
        dumped = obj.display
        if include:
            exclude_attributes = list(set(dumped.keys()) - set(include))
            exclude = set(exclude + exclude_attributes) if exclude else exclude_attributes
        if exclude:
            for exclude_attribute in exclude:
                dumped.pop(exclude_attribute, None)
        return dumped

    @staticmethod
    def _create_default_logger():
        return logging.getLogger(DEFAULT_LOGGER_NAME)
