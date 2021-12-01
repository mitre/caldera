from marshmallow.schema import SchemaMeta
from typing import Any

from app.api.v2.managers.operation_api_manager import OperationApiManager
from app.utility.base_world import BaseWorld


class ScheduleApiManager(OperationApiManager):
    def __init__(self, services):
        super().__init__(services)
        self.services = services

    def find_and_update_object(self, ram_key: str, data: dict, search: dict = None):
        return super(OperationApiManager, self).find_and_update_object(ram_key, data, search)

    def update_object(self, obj: Any, data: dict):
        return super(OperationApiManager, self).update_object(obj, data)

    def create_object_from_schema(self, schema: SchemaMeta, data: dict, access: BaseWorld.Access):
        return super(OperationApiManager, self).create_object_from_schema(schema, data, access)

    async def validate_and_setup_task(self, data: dict, access: BaseWorld.Access):
        if data.get('state'):
            await self.validate_operation_state(data, None)
        return await self.setup_operation(data, access)
