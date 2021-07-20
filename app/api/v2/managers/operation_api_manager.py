import asyncio
import copy

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
        planner_name = data.pop('planner', {}).get('name', '')
        planner = await self._construct_planner(planner_name)
        adversary_data = data.pop('adversary', {})
        adversary_id = adversary_data.get('adversary_id', '')
        adversary = await self._construct_adversary(adversary_id)
        group_data = data.pop('host_group', '')
        agents = await self._construct_agents(group_data)
        sources = await self.services['data_svc'].locate('sources', match=dict(name='basic'))
        allowed = self._get_allowed_from_access(access)
        operation = Operation(name=data.pop('name'), id=data.pop('id', ''), planner=planner, agents=agents,
                              adversary=adversary, jitter=data.pop('jitter', '2/8'), source=next(iter(sources), None),
                              state=data.pop('state', 'running'), autonomous=int(data.pop('autonomous', 1)),
                              access=allowed, obfuscator=data.pop('obfuscator', 'plain-text'),
                              auto_close=bool(int(data.pop('auto_close', 0))),
                              visibility=int(data.pop('visibility', '50')),
                              use_learning_parsers=bool(int(data.pop('use_learning_parsers', 0))))
        operation.set_start_details()
        return operation

    async def _construct_planner(self, planner_name: str):
        planner = (await self.services['data_svc'].locate('planners', match=dict(name=planner_name)))
        if not planner:
            planner = await self.services['data_svc'].locate('planners', match=dict(name='atomic'))
        return planner[0]

    async def _construct_adversary(self, adversary_id: str):
        adv = await self.services['data_svc'].locate('adversaries', match=dict(adversary_id=adversary_id))
        if adv:
            return copy.deepcopy(adv[0])
        return Adversary.load(dict(adversary_id='ad-hoc', name='ad-hoc', description='an empty adversary profile',
                                   atomic_ordering=[]))

    async def _construct_agents(self, agents: list):
        agent_list = []
        if agents:
            for agent in agents:
                result = await self.services['data_svc'].locate('agents', match=dict(paw=agent.get('paw')))
                if result:
                    agent_list.append(copy.deepcopy(result[0]))
            return agent_list
        return await self.services['data_svc'].locate('agents')

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
