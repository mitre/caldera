import asyncio

from marshmallow.schema import SchemaMeta
from app.utility.base_world import BaseWorld

from app.api.v2.managers.base_api_manager import BaseApiManager
from app.api.v2.responses import JsonHttpNotFound, JsonHttpForbidden


class OperationApiManager(BaseApiManager):
    def __init__(self, services):
        super().__init__(data_svc=services['data_svc'], file_svc=services['file_svc'])
        self.services = services

    async def get_operation_report(self, operation_id: str, access: dict):
        operation = await self.get_operation_object(operation_id, access)
        report = await operation.report(file_svc=self._file_svc, data_svc=self._data_svc)
        return report

    async def create_object_from_schema(self, schema: SchemaMeta, data: dict, access: BaseWorld.Access):
        obj_schema = schema()
        operation = obj_schema.load(data)
        operation.access = self._get_allowed_from_access(access)
        operation.set_start_details()
        operation.store(self._data_svc.ram)
        asyncio.get_event_loop().create_task(operation.run(self.services))
        return operation

    """Object Creation Helpers"""
    async def get_operation_object(self, operation_id: str, access: dict):
        try:
            operation = (await self._data_svc.locate('operations', {'id': operation_id}))[0]
        except IndexError:
            raise JsonHttpNotFound(f'Operation not found: {operation_id}')
        if operation.match(access):
            return operation
        raise JsonHttpForbidden(f'Cannot view operation due to insufficient permissions: {operation_id}')
