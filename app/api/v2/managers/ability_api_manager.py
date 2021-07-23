import re
import uuid
import os
import yaml

from typing import Any

from app.api.v2.managers.base_api_manager import BaseApiManager
from app.api.v2.responses import JsonHttpBadRequest
from app.utility.base_world import BaseWorld


class AbilityApiManager(BaseApiManager):
    def __init__(self, data_svc, file_svc):
        super().__init__(data_svc=data_svc, file_svc=file_svc)

    async def create_on_disk_object(self, data: dict, access: dict, ram_key: str, id_property: str, obj_class: type):
        self._validate_ability_data(create=True, data=data)
        obj_id = data.get('id')
        tactic_dir = os.path.join('data', 'abilities', data.get('tactic'))
        if not os.path.exists(tactic_dir):
            os.makedirs(tactic_dir)
        file_path = os.path.join(tactic_dir, '%s.yml' % obj_id)
        allowed = self._get_allowed_from_access(access)
        await self._save_and_reload_object(file_path, data, obj_class, allowed)
        return next(self.find_objects(ram_key, {id_property: obj_id}))

    async def replace_on_disk_object(self, obj: Any, data: dict, ram_key: str, id_property: str):
        self._validate_ability_data(create=True, data=data)
        return await super().replace_on_disk_object(obj, data, ram_key, id_property)

    async def update_on_disk_object(self, obj: Any, data: dict, ram_key: str, id_property: str, obj_class: type):
        self._validate_ability_data(create=False, data=data)
        obj_id = getattr(obj, id_property)
        file_path = await self._get_existing_object_file_path(obj_id, ram_key)
        existing_obj_data = dict(self.strip_yml(file_path)[0][0])
        existing_obj_data.update(data)
        await self._save_and_reload_object(file_path, existing_obj_data, obj_class, obj.access)
        return next(self.find_objects(ram_key, {id_property: obj_id}))

    '''Helpers'''
    def _validate_ability_data(self, create: bool, data: dict):
        # Correct ability_id key for ability file saving.
        data['id'] = data.pop('ability_id', '')

        # If a new ability is being created, ensure required fields present.
        if create:
            # Set ability ID if undefined
            if not data['id']:
                data['id'] = str(uuid.uuid4())
            if 'tactic' not in data:
                raise JsonHttpBadRequest(f'Cannot create ability {data["id"]} due to missing tactic')
            if not data.get('executors'):
                raise JsonHttpBadRequest(f'Cannot create ability {data["id"]}: at least one executor required')
        # Validate ID, used for file creation
        validator = re.compile(r'^[a-zA-Z0-9-_]+$')
        if 'id' in data and not validator.match(data['id']):
            raise JsonHttpBadRequest(f'Invalid ability ID {data["id"]}. IDs can only contain '
                                     'alphanumeric characters, hyphens, and underscores.')

        # Validate tactic, used for directory creation, lower case if present
        if 'tactic' in data:
            if not validator.match(data['tactic']):
                raise JsonHttpBadRequest(f'Invalid ability tactic {data["tactic"]}. Tactics can only contain '
                                         'alphanumeric characters, hyphens, and underscores.')
            data['tactic'] = data['tactic'].lower()

    async def _save_and_reload_object(self, file_path: str, data: dict, obj_type: type, access: BaseWorld.Access):
        await self._file_svc.save_file(file_path, yaml.dump([data], encoding='utf-8', sort_keys=False),
                                       '', encrypt=False)
        await self._data_svc.remove('abilities', dict(ability_id=data['id']))
        await self._data_svc.load_ability_file(file_path, access)
