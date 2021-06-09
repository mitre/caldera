import logging
from marshmallow.schema import SchemaMeta
from typing import List


DEFAULT_LOGGER_NAME = 'rest_api_manager'


class BaseApiManager:
    def __init__(self, data_svc, logger=None):
        self._data_svc = data_svc
        self._log = logger or self._create_default_logger()

    @property
    def log(self):
        return self._log

    def find_objects(self, object_name: str, search: dict = None):
        """Find objects matching the given criteria"""
        for obj in self._data_svc.ram[object_name]:
            if not search or obj.match(search):
                yield obj

    def find_and_dump_objects(self, object_name: str, search: dict = None, sort: str = None, include: List[str] = None,
                              exclude: List[str] = None):
        matched_objs = []
        for obj in self.find_objects(object_name, search):
            dumped_obj = self.dump_object_with_filters(obj, include, exclude)
            matched_objs.append(dumped_obj)
        return sorted(matched_objs, key=lambda p: p.get(sort, 0))

    def find_and_dump_object(self, object_name: str, search: dict = None, include: List[str] = None,
                             exclude: List[str] = None):
        for obj in self.find_objects(object_name, search):
            return self.dump_object_with_filters(obj, include, exclude)

    def store_json_as_schema(self, schema: SchemaMeta, data: dict):
        obj_schema = schema()
        obj = obj_schema.load(data)
        obj.store(self._data_svc.ram)
        return obj

    def update_object(self, object_name: str, data: dict, search: dict = None):
        for obj in self.find_objects(object_name, search):
            for key, value in data.items():
                obj.update(key, value)
            return obj

    @staticmethod
    def dump_object_with_filters(obj, include: List[str] = None, exclude: List[str] = None):
        dumped = obj.display
        if include:
            exclude_attributes = list(set(dumped.keys()) - set(include))
            exclude = list(set(exclude + exclude_attributes)) if exclude else exclude_attributes
        if exclude:
            for exclude_attribute in exclude:
                dumped.pop(exclude_attribute, None)
        return dumped

    @staticmethod
    def _create_default_logger():
        return logging.getLogger(DEFAULT_LOGGER_NAME)
