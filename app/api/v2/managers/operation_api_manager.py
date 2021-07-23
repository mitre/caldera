import asyncio

from marshmallow.schema import SchemaMeta
from typing import Any

from app.api.v2.managers.base_api_manager import BaseApiManager
from app.api.v2.responses import JsonHttpNotFound, JsonHttpForbidden, JsonHttpBadRequest
from app.objects.c_adversary import Adversary, AdversarySchema
from app.objects.c_operation import Operation, OperationSchema
from app.objects.c_planner import PlannerSchema
from app.objects.c_source import SourceSchema
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
        operation = await self.setup_operation(data, access)
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

    async def setup_operation(self, data: dict, access: BaseWorld.Access):
        """Applies default settings to an operation if data is missing."""
        planner_id = data.pop('planner', {}).get('id', '')
        data['planner'] = await self._construct_and_dump_planner(planner_id)
        adversary_id = data.pop('adversary', {}).get('adversary_id', '')
        data['adversary'] = await self._construct_and_dump_adversary(adversary_id)
        fact_source_id = data.pop('source', {}).get('id', '')
        data['source'] = await self._construct_and_dump_source(fact_source_id)
        operation = OperationSchema().load(data)
        await operation.update_operation_agents(self.services)
        allowed = self._get_allowed_from_access(access)
        operation.set_operation_access(allowed)
        operation.set_start_details()
        return operation

    async def _construct_and_dump_planner(self, planner_id: str):
        planner = (await self.services['data_svc'].locate('planners', match=dict(id=planner_id)))
        if not planner:
            planner = (await self.services['data_svc'].locate('planners', match=dict(name='atomic')))
        return PlannerSchema().dump(planner[0])

    async def _construct_and_dump_adversary(self, adversary_id: str):
        adv = await self.services['data_svc'].locate('adversaries', match=dict(adversary_id=adversary_id))
        if not adv:
            adv = Adversary.load(dict(adversary_id='ad-hoc', name='ad-hoc', description='an empty adversary profile',
                                      atomic_ordering=[]))
        else:
            adv = adv[0]
        return AdversarySchema().dump(adv)

    async def _construct_and_dump_source(self, source_id: str):
        source = await self.services['data_svc'].locate('sources', match=dict(id=source_id))
        if not source:
            source = (await self.services['data_svc'].locate('sources', match=dict(name='basic')))
        return SourceSchema().dump(source[0])

    async def validate_operation_state(self, data: dict, existing: Operation = None):
        if not existing:
            if data.get('state') in Operation.get_finished_states():
                raise JsonHttpBadRequest('Cannot create a finished operation.')
            elif data.get('state') not in Operation.get_states():
                raise JsonHttpBadRequest('state must be one of {}'.format(Operation.get_states()))
        else:
            if await existing.is_finished() and data.get('state') not in Operation.get_finished_states():
                raise JsonHttpBadRequest('This operation has already finished.')
            elif 'state' in data and data.get('state') not in Operation.get_states():
                raise JsonHttpBadRequest('state must be one of {}'.format(Operation.get_states()))
