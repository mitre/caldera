from marshmallow.schema import SchemaMeta

from app.api.v2.managers.operation_api_manager import OperationApiManager
from app.objects.c_operation import OperationSchema
from app.utility.base_world import BaseWorld


class ScheduleApiManager(OperationApiManager):
    def __init__(self, services):
        super().__init__(services)
        self.services = services

    async def create_object_from_schema(self, schema: SchemaMeta, data: dict,
                                        access: BaseWorld.Access):
        super(OperationApiManager, self).create_object_from_schema(schema, data, access)

    async def setup_operation(self, data: dict, access: BaseWorld.Access):
        """Applies default settings to an operation if data is missing."""
        if data.get('state'):
            await self.validate_operation_state(data, None)
        planner_id = data.pop('planner', {}).get('id', '')
        data['planner'] = await self._construct_and_dump_planner(planner_id)
        adversary_id = data.pop('adversary', {}).get('adversary_id', '')
        data['adversary'] = await self._construct_and_dump_adversary(adversary_id)
        fact_source_id = data.pop('source', {}).get('id', '')
        data['source'] = await self._construct_and_dump_source(fact_source_id)
        operation = OperationSchema().load(data)
        await operation.update_operation_agents(self.services)
        allowed = self._get_allowed_from_access(access)
        operation.access = allowed
        return operation
