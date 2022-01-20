import logging
import os
import uuid
import yaml

from marshmallow.schema import SchemaMeta
from typing import Any, List
from base64 import b64encode, b64decode

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

    def find_objects(self, ram_key: str, search: dict = None):
        """Find objects matching the given criteria"""
        for obj in self._data_svc.ram[ram_key]:
            if not search or obj.match(search):
                yield obj

    def find_object(self, ram_key: str, search: dict = None):
        for obj in self.find_objects(ram_key, search):
            return obj

    def find_and_dump_objects(self, ram_key: str, search: dict = None, sort: str = None, include: List[str] = None,
                              exclude: List[str] = None):
        matched_objs = []
        for obj in self.find_objects(ram_key, search):
            dumped_obj = self.dump_object_with_filters(obj, include, exclude)
            matched_objs.append(dumped_obj)
        sorted_objs = sorted(matched_objs, key=lambda p: p.get(sort, 0))
        if sorted_objs and sort in sorted_objs[0]:
            return sorted(sorted_objs,
                          key=lambda x: 0 if x[sort] == self._data_svc.get_config(f"objects.{ram_key}.default") else 1)
        return sorted_objs

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

    def create_object_from_schema(self, schema: SchemaMeta, data: dict, access: BaseWorld.Access):
        obj_schema = schema()
        obj = obj_schema.load(data)
        obj.access = self._get_allowed_from_access(access)
        return obj.store(self._data_svc.ram)

    async def create_on_disk_object(self, data: dict, access: dict, ram_key: str, id_property: str, obj_class: type):
        obj_id = data.get(id_property) or str(uuid.uuid4())
        data[id_property] = obj_id

        file_path = await self._get_new_object_file_path(data[id_property], ram_key)
        allowed = self._get_allowed_from_access(access)
        await self._save_and_reload_object(file_path, data, obj_class, allowed)
        return next(self.find_objects(ram_key, {id_property: obj_id}))

    def _get_allowed_from_access(self, access) -> BaseWorld.Access:
        if self._data_svc.Access.HIDDEN in access['access']:
            return self._data_svc.Access.HIDDEN
        elif self._data_svc.Access.BLUE in access['access']:
            return self._data_svc.Access.BLUE
        else:
            return self._data_svc.Access.RED

    def find_and_update_object(self, ram_key: str, data: dict, search: dict = None):
        for obj in self.find_objects(ram_key, search):
            new_obj = self.update_object(obj, data)
            return new_obj

    def update_object(self, obj: Any, data: dict):
        dumped_obj = obj.schema.dump(obj)
        for key, value in dumped_obj.items():
            if key not in data:
                data[key] = value
        return self.replace_object(obj, data)

    def replace_object(self, obj: Any, data: dict):
        new_obj = obj.schema.load(data)
        return new_obj.store(self._data_svc.ram)

    async def find_and_update_on_disk_object(self, data: dict, search: dict, ram_key: str, id_property: str, obj_class: type):
        for obj in self.find_objects(ram_key, search):
            new_obj = await self.update_on_disk_object(obj, data, ram_key, id_property, obj_class)
            return new_obj

    async def update_on_disk_object(self, obj: Any, data: dict, ram_key: str, id_property: str, obj_class: type):
        obj_id = getattr(obj, id_property)
        file_path = await self._get_existing_object_file_path(obj_id, ram_key)

        existing_obj_data = dict(self.strip_yml(file_path)[0])
        existing_obj_data.update(data)

        await self._save_and_reload_object(file_path, existing_obj_data, obj_class, obj.access)
        return next(self.find_objects(ram_key, {id_property: obj_id}))

    async def replace_on_disk_object(self, obj: Any, data: dict, ram_key: str, id_property: str):
        obj_id = getattr(obj, id_property)
        file_path = await self._get_existing_object_file_path(obj_id, ram_key)

        await self._save_and_reload_object(file_path, data, type(obj), obj.access)
        return next(self.find_objects(ram_key, {id_property: obj_id}))

    async def remove_object_from_memory_by_id(self, identifier: str, ram_key: str, id_property: str):
        await self._data_svc.remove(ram_key, {id_property: identifier})

    async def remove_object_from_disk_by_id(self, identifier: str, ram_key: str):
        file_path = await self._get_existing_object_file_path(identifier, ram_key)

        if os.path.exists(file_path):
            os.remove(file_path)

    @staticmethod
    async def _get_new_object_file_path(identifier: str, ram_key: str) -> str:
        """Create file path for new object"""
        return os.path.join('data', ram_key, f'{identifier}.yml')

    async def _get_existing_object_file_path(self, identifier: str, ram_key: str) -> str:
        """Find file path for existing object (by id)"""
        _, file_path = await self._file_svc.find_file_path(f'{identifier}.yml', location=ram_key)
        if not file_path:
            file_path = await self._get_new_object_file_path(identifier, ram_key)
        return file_path

    async def _save_and_reload_object(self, file_path: str, data: dict, obj_type: type, access: BaseWorld.Access):
        """Save data as YAML and reload from disk into memory"""
        await self._file_svc.save_file(file_path, yaml.dump(data, encoding='utf-8', sort_keys=False), '', encrypt=False)
        await self._data_svc.load_yaml_file(obj_type, file_path, access)

    @staticmethod
    def _create_default_logger():
        return logging.getLogger(DEFAULT_LOGGER_NAME)

    @staticmethod
    def _encode_string(s):
        return str(b64encode(s.encode()), 'utf-8')

    @staticmethod
    def _decode_string(s):
        return str(b64decode(s), 'utf-8')
