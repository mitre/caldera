import re
import uuid
import os
import yaml

from typing import Any

from app.api.v2.managers.base_api_manager import BaseApiManager
from app.api.v2.responses import JsonHttpBadRequest
from app.objects.c_ability import AbilitySchema
from app.utility.base_world import BaseWorld


class AbilityApiManager(BaseApiManager):
    def __init__(self, data_svc, file_svc):
        super().__init__(data_svc=data_svc, file_svc=file_svc)

    async def create_on_disk_object(self, data: dict, access: dict, ram_key: str, id_property: str, obj_class: type):
        self._validate_ability_data(create=True, data=data)
        obj_id = data.get('id')
        file_path = self._create_ability_filepath(data.get('tactic'), obj_id)
        allowed = self._get_allowed_from_access(access)
        await self._save_and_reload_object(file_path, data, obj_class, allowed)
        await self._data_svc.create_or_update_everything_adversary()
        return next(self.find_objects(ram_key, {id_property: obj_id}))

    async def replace_on_disk_object(self, obj: Any, data: dict, ram_key: str, id_property: str):
        self._validate_ability_data(create=True, data=data)
        obj_id = getattr(obj, id_property)
        file_path = await self._get_existing_object_file_path(obj_id, ram_key)
        if data.get('tactic') not in file_path:
            await self.remove_object_from_disk_by_id(obj_id, ram_key)
            file_path = self._create_ability_filepath(data.get('tactic'), obj_id)
        await self._save_and_reload_object(file_path, data, type(obj), obj.access)
        return next(self.find_objects(ram_key, {id_property: obj_id}))

    async def remove_object_from_disk_by_id(self, identifier: str, ram_key: str):
        await super().remove_object_from_disk_by_id(identifier, ram_key)
        await self._data_svc.create_or_update_everything_adversary()

    async def update_on_disk_object(self, obj: Any, data: dict, ram_key: str, id_property: str, obj_class: type):
        obj_id = getattr(obj, id_property)
        file_path = await self._get_existing_object_file_path(obj_id, ram_key)
        existing_obj_data = AbilitySchema().dump(obj)
        existing_obj_data.update(data)
        self._validate_ability_data(create=False, data=existing_obj_data)
        if existing_obj_data.get('tactic') not in file_path:
            await self.remove_object_from_disk_by_id(obj_id, ram_key)
            file_path = self._create_ability_filepath(data.get('tactic'), obj_id)
        await self._save_and_reload_object(file_path, existing_obj_data, obj_class, obj.access)
        return next(self.find_objects(ram_key, {id_property: obj_id}))

    def _validate_ability_data(self, create: bool, data: dict):
        # Correct ability_id key for ability file saving.
        data['id'] = data.pop('ability_id', '')

        # If a new ability is being created, ensure required fields present.
        if create:
            # Set ability ID if undefined
            if not data['id']:
                data['id'] = str(uuid.uuid4())
            if not data.get('name'):
                raise JsonHttpBadRequest(f'Cannot create ability {data["id"]} due to missing name')
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

        if 'executors' in data and not data.get('executors'):
            raise JsonHttpBadRequest(f'Cannot create ability {data["id"]}: at least one executor required')

        if 'name' in data and not data.get('name'):
            raise JsonHttpBadRequest(f'Cannot create ability {data["id"]} due to missing name')

    def _create_ability_filepath(self, tactic: str, obj_id: str):
        tactic_dir = os.path.join('data', 'abilities', tactic)
        if not os.path.exists(tactic_dir):
            os.makedirs(tactic_dir)
        return os.path.join(tactic_dir, '%s.yml' % obj_id)

    async def upload_ability_file(self, file_data: bytes, filename: str, access: dict):
        """Upload a YAML ability file, validate it, save to disk, and load into memory."""
        # Validate file extension
        if not filename.lower().endswith(('.yml', '.yaml')):
            raise JsonHttpBadRequest('Invalid file type. Only .yml and .yaml files are accepted.')

        # Parse YAML
        try:
            # Ensure we pass a text string to yaml.safe_load. PyYAML accepts strings or file-like objects.
            # The test fixtures pass bytes; decode bytes/bytearray to str before parsing.
            if isinstance(file_data, (bytes, bytearray)):
                try:
                    file_text = file_data.decode('utf-8')
                except UnicodeDecodeError:
                    # Fallback to latin-1 to preserve byte values if utf-8 fails
                    file_text = file_data.decode('latin-1')
            else:
                file_text = file_data
            parsed = yaml.safe_load(file_text)
        except yaml.YAMLError as e:
            raise JsonHttpBadRequest(f'Invalid YAML: {e}')

        # Handle list-wrapped abilities (common format: list of one dict)
        if isinstance(parsed, list):
            if len(parsed) == 0:
                raise JsonHttpBadRequest('YAML file contains an empty list.')
            parsed = parsed[0]

        if not isinstance(parsed, dict):
            raise JsonHttpBadRequest('YAML file must contain a mapping/dictionary.')

        # Extract required fields
        ability_id = parsed.get('id') or parsed.get('ability_id')
        if not ability_id:
            raise JsonHttpBadRequest('Missing required field: "id" or "ability_id".')
        name = parsed.get('name')
        if not name:
            raise JsonHttpBadRequest('Missing required field: "name".')
        tactic = parsed.get('tactic')
        if not tactic:
            raise JsonHttpBadRequest('Missing required field: "tactic".')

        # Validate ID and tactic format
        validator = re.compile(r'^[a-zA-Z0-9-_]+$')
        if not validator.match(str(ability_id)):
            raise JsonHttpBadRequest(f'Invalid ability ID "{ability_id}". '
                                     'IDs can only contain alphanumeric characters, hyphens, and underscores.')
        if not validator.match(tactic):
            raise JsonHttpBadRequest(f'Invalid tactic "{tactic}". '
                                     'Tactics can only contain alphanumeric characters, hyphens, and underscores.')

        tactic = tactic.lower()
        parsed['tactic'] = tactic
        parsed['id'] = ability_id
        # Normalize keys so downstream loaders don't receive duplicate ability_id
        parsed.pop('ability_id', None)

        # Check for duplicates
        existing = list(self.find_objects('abilities', dict(ability_id=str(ability_id))))
        if existing:
            raise JsonHttpBadRequest(f'Ability with id already exists: {ability_id}')

        # Determine save path and create directory if needed
        tactic_dir = os.path.join('data', 'abilities', tactic)
        if not os.path.exists(tactic_dir):
            os.makedirs(tactic_dir)
        file_path = os.path.join(tactic_dir, f'{ability_id}.yml')

        # Write the file
        with open(file_path, 'wb') as f:
            # Dump as bytes using explicit encoding
            f.write(yaml.dump([parsed], encoding='utf-8', sort_keys=False))

        # Load into memory
        allowed = self._get_allowed_from_access(access)
        await self._data_svc.load_ability_file(file_path, allowed)

        # Return the loaded ability
        loaded = self.find_objects('abilities', dict(ability_id=str(ability_id)))
        if loaded:
            return list(loaded)[0]
        raise JsonHttpBadRequest(f'Ability was saved but could not be loaded into memory: {ability_id}')

    async def _save_and_reload_object(self, file_path: str, data: dict, obj_type: type, access: BaseWorld.Access):
        await self._file_svc.save_file(file_path, yaml.dump([data], encoding='utf-8', sort_keys=False),
                                       '', encrypt=False)
        await self._data_svc.remove('abilities', dict(ability_id=data['id']))
        await self._data_svc.load_ability_file(file_path, access)
