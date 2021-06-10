import logging
import os
import yaml

from marshmallow.schema import SchemaMeta
from typing import Any, List

from app.utility.base_world import BaseWorld


DEFAULT_LOGGER_NAME = 'rest_api_manager'


class BaseApiManager(BaseWorld):
    def __init__(self, data_svc, file_svc, logger=None):
        self._data_svc = data_svc
        self._file_svc = file_svc
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

    def find_and_update_object(self, object_name: str, data: dict, search: dict = None):
        for obj in self.find_objects(object_name, search):
            new_obj = self.update_object(obj, data)
            return new_obj

    def create_object_from_schema(self, schema: SchemaMeta, data: dict):
        obj_schema = schema()
        obj = obj_schema.load(data)
        obj.store(self._data_svc.ram)
        return obj

    def update_object(self, obj: Any, data: dict):
        dumped_obj = obj.schema.dump(obj)
        for key, value in dumped_obj.items():
            if key not in data:
                data[key] = value
        return self.replace_object(obj, data)

    def replace_object(self, obj: Any, data: dict):
        new_obj = obj.schema.load(data)
        new_obj.store(self._data_svc.ram)
        return new_obj

    async def remove_object_from_memory_by_id(self, ram_key: str, id_value: str, id_attribute: str):
        await self._data_svc.remove(ram_key, {id_attribute: id_value})

    async def remove_object_from_disk_by_id(self, ram_key: str, id_value: str):
        _, file_path = await self._file_svc.find_file_path(f'{id_value}.yml', location='data')
        if not file_path:
            file_path = f'data/{ram_key}/{id_value}.yml'

        if os.path.exists(file_path):
            os.remove(file_path)

    @staticmethod
    def dump_object_with_filters(obj: Any, include: List[str] = None, exclude: List[str] = None) -> dict:
        dumped = obj.display
        if include:
            exclude_attributes = list(set(dumped.keys()) - set(include))
            exclude = set(exclude + exclude_attributes) if exclude else exclude_attributes
        if exclude:
            for exclude_attribute in exclude:
                dumped.pop(exclude_attribute, None)
        return dumped

    def _get_allowed_from_access(self, access) -> BaseWorld.Access:
        if self._data_svc.Access.HIDDEN in access['access']:
            return self._data_svc.Access.HIDDEN
        elif self._data_svc.Access.BLUE in access['access']:
            return self._data_svc.Access.BLUE
        else:
            return self._data_svc.Access.RED

    async def _get_new_object_file_path(self, ram_key: str, identifier: str) -> str:
        """Create file path for new object"""
        return f'data/{ram_key}/{identifier}.yml'

    async def _get_existing_object_file_path(self, identifier: str) -> str:
        """Find file path for existing object (by id)"""
        _, file_path = await self._file_svc.find_file_path(f'{identifier}.yml', location='data')
        return file_path

    async def _save_and_reload_object(self, file_path: str, data: dict, obj_type: type, access: BaseWorld.Access):
        """Save data as YAML and reload from disk into memory"""
        await self._file_svc.save_file(file_path, yaml.dump(data, encoding='utf-8', sort_keys=False), '', encrypt=False)
        await self._data_svc.load_yaml_file(obj_type, file_path, access)

    @staticmethod
    def _create_default_logger():
        return logging.getLogger(DEFAULT_LOGGER_NAME)
