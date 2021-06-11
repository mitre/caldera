import re
import uuid

from typing import Any

from app.api.v2.managers.base_api_manager import BaseApiManager
from app.api.v2.responses import JsonHttpBadRequest


class AbilityApiManager(BaseApiManager):
    def __init__(self, data_svc, file_svc):
        super().__init__(data_svc=data_svc, file_svc=file_svc)

    def validate_ability_data(self, create: bool, data: dict):
        # If a new ability is being created, ensure required fields present.
        if create:
            # Set ability ID if undefined
            if 'ability_id' not in data:
                data['ability_id'] = str(uuid.uuid4())
            if 'tactic' not in data:
                raise JsonHttpBadRequest(f'Cannot create ability {data["ability_id"]} due to missing tactic')
            if not data['executors']:
                raise JsonHttpBadRequest(f'Cannot create ability {data["ability_id"]}: at least one executor required')
        # Validate ID, used for file creation
        validator = re.compile(r'^[a-zA-Z0-9-_]+$')
        if 'ability_id' in data and not validator.match(data['ability_id']):
            raise JsonHttpBadRequest(f'Invalid ability ID {data["ability_id"]}. IDs can only contain '
                                     'alphanumeric characters, hyphens, and underscores.')

        # Validate tactic, used for directory creation, lower case if present
        if 'tactic' in data:
            if not validator.match(data['tactic']):
                raise JsonHttpBadRequest(f'Invalid ability tactic {data["tactic"]}. Tactics can only contain '
                                         'alphanumeric characters, hyphens, and underscores.')
            data['tactic'] = data['tactic'].lower()

        # Validate platforms, ability will not be loaded if empty
        if 'executors' in data and not data['executors']:
            raise JsonHttpBadRequest('At least one executor is required to save ability.')

    async def create_on_disk_object(self, data: dict, access: dict, ram_key: str, id_property: str, obj_class: type):
        self.validate_ability_data(create=True, data=data)
        return await super().create_on_disk_object(data, access, ram_key, id_property, obj_class)

    async def replace_on_disk_object(self, obj: Any, data: dict, ram_key: str, id_property: str):
        self.validate_ability_data(create=False, data=data)
        return await super().replace_on_disk_object(obj, data, ram_key, id_property)

    async def update_on_disk_object(self, obj: Any, data: dict, ram_key: str, id_property: str, obj_class: type):
        self.validate_ability_data(create=False, data=data)
        return await super().update_on_disk_object(obj, data, ram_key, id_property, obj_class)
