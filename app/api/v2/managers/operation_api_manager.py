import asyncio

from marshmallow.schema import SchemaMeta
from typing import Any

from app.api.v2.managers.base_api_manager import BaseApiManager
from app.api.v2.responses import JsonHttpNotFound, JsonHttpForbidden, JsonHttpBadRequest
from app.objects.c_adversary import Adversary
from app.objects.c_operation import Operation
from app.utility.base_world import BaseWorld


class OperationApiManager(BaseApiManager):
    def __init__(self, services):
        super().__init__(data_svc=services['data_svc'], file_svc=services['file_svc'])
        self.services = services

    async def get_operation_report(self, operation_id: str, access: dict):
        operation = await self.get_operation_object(operation_id, access)
        report = await operation.report(file_svc=self._file_svc, data_svc=self._data_svc)
        return report

    async def create_object_from_schema(self, schema: SchemaMeta, data: dict,
                                        access: BaseWorld.Access, existing_operation: Operation = None):
        if data.get('state'):
            await self.validate_operation_state(data, existing_operation)
        obj_schema = schema()
        operation = obj_schema.load(data)
        await self.setup_operation(operation, access)
        operation.store(self._data_svc.ram)
        asyncio.get_event_loop().create_task(operation.run(self.services))
        return operation

    async def find_and_update_object(self, ram_key: str, data: dict, search: dict = None):
        for obj in self.find_objects(ram_key, search):
            new_obj = await self.update_object(obj, data)
            return new_obj

    async def update_object(self, obj: Any, data: dict):
        await self.validate_operation_state(data, obj)
        return super().update_object(obj, data)

    """Object Creation Helpers"""
    async def get_operation_object(self, operation_id: str, access: dict):
        try:
            operation = (await self._data_svc.locate('operations', {'id': operation_id}))[0]
        except IndexError:
            raise JsonHttpNotFound(f'Operation not found: {operation_id}')
        if operation.match(access):
            return operation
        raise JsonHttpForbidden(f'Cannot view operation due to insufficient permissions: {operation_id}')

    async def setup_operation(self, operation: Operation, access: BaseWorld.Access):
        """Applies default settings to an operation if data is missing."""
        if not operation.planner:
            operation.planner = (await self.services['data_svc'].locate('planners', match=dict(name='atomic')))[0]
        if not operation.adversary:
            operation.adversary = Adversary.load(dict(adversary_id='ad-hoc', name='ad-hoc',
                                                      description='an empty adversary profile',
                                                      atomic_ordering=[]))
        if not operation.source:
            sources = await self.services['data_svc'].locate('sources', match=dict(name='basic'))
            operation.source = next(iter(sources), None)
        if not operation.group:
            operation.agents = await self.services['data_svc'].locate('agents')
        operation.access = self._get_allowed_from_access(access)
        operation.set_start_details()

    async def validate_operation_state(self, data: dict, existing: Operation = None):
        if not existing:
            if data.get('state') in Operation.get_finished_states():
                raise JsonHttpBadRequest('Cannot create a finished operation.')
            elif data.get('state') not in Operation.get_states():
                raise JsonHttpBadRequest('state must be one of {}'.format(Operation.get_states()))
        else:
            # Ensure that we update the state of a preexisting operation appropriately.
            if await existing.is_finished() and data.get('state') not in Operation.get_finished_states():
                raise JsonHttpBadRequest('This operation has already finished.')
            elif data.get('state') not in Operation.get_states():
                raise JsonHttpBadRequest('state must be one of {}'.format(Operation.get_states()))
