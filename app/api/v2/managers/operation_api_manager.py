from marshmallow.schema import SchemaMeta

from app.api.v2.managers.base_api_manager import BaseApiManager
from app.api.v2.responses import JsonHttpNotFound, JsonHttpForbidden
from app.objects.secondclass.c_link import LinkSchema, Link
from app.objects.secondclass.c_executor import Executor
from app.objects.c_ability import Ability
from app.utility.base_world import BaseWorld

import uuid


class OperationApiManager(BaseApiManager):
    def __init__(self, data_svc, file_svc):
        super().__init__(data_svc=data_svc, file_svc=file_svc)

    async def get_operation_report(self, operation_id: str, access: dict):
        operation = await self.get_operation_object(operation_id, access)
        report = await operation.report(file_svc=self._file_svc, data_svc=self._data_svc)
        return report

    async def get_operation_links(self, operation_id: str, access: dict):
        operation = await self.get_operation(operation_id, access)
        links = [link.display for link in operation.chain]
        return links

    async def get_operation_link(self, operation_id: str, link_id: str, access: dict):
        operation = await self.get_operation(operation_id, access)
        for link in operation.chain:
            if link.id == link_id:
                return link.display
        raise JsonHttpNotFound(f'Link {link_id} was not found in Operation {operation_id}')

    async def create_or_update_operation_link(self, operation_id: str, link_id: str,
                                              link_data: dict, access: BaseWorld.Access):
        operation = await self.get_operation(operation_id, access)
        existing_link = None
        for entry in operation.chain:
            if entry.id == link_id:
                existing_link = entry
                break
        if existing_link and existing_link.access not in access['access']:
            raise JsonHttpForbidden(f'Cannot update link {link_id} due to insufficient permissions.')
        if not existing_link and 'id' not in link_data:
            link_data['id'] = str(uuid.uuid4())

        new_link = self.create_secondclass_object_from_schema(LinkSchema, link_data, access)
        if existing_link:
            operation.chain.remove(entry)
        operation.add_link(new_link)
        return new_link.display

    async def create_potential_link(self, operation_id: str, link_data: dict, access: BaseWorld.Access):
        operation = await self.get_operation(operation_id, access)
        agent = await self.get_agent(access, link_data)
        if link_data['executor']['name'] not in agent.executors:
            return dict(error='Agent missing specified executor')

        encoded_command = self._encode_string(link_data['executor']['command'])
        ability_id = str(uuid.uuid4())

        executor = Executor(name=link_data['executor']['name'], platform=agent.platform,
                            command=link_data['executor']['command'])
        ability = Ability(ability_id=ability_id, tactic='auto-generated', technique_id='auto-generated',
                          technique_name='auto-generated', name='Manual Command', description='Manual command ability',
                          executors=[executor])
        link = Link.load(dict(command=encoded_command, paw=agent.paw, cleanup=0, ability=ability, score=0, jitter=2,
                              executor=executor, status=operation.link_status()))
        link.apply_id(agent.host)
        operation.add_link(link)
        return link.display

    async def get_potential_links(self, operation_id: str, access: dict):
        operation = await self.get_operation(operation_id, access)
        potential_links = [potential_link.display for potential_link in operation.potential_links]
        return potential_links

    async def get_potential_links_by_paw(self, operation_id: str, paw: str, access: dict):
        operation = await self.get_operation(operation_id, access)
        output_links = []
        for link in operation.potential_links:
            if link.paw == paw:
                output_links.append(link.display)
        if not output_links:
            raise JsonHttpNotFound(f'Agent {paw} was not found in potential links for Operation {operation_id}')
        return output_links

    """Object Creation Helpers"""
    async def get_operation_object(self, operation_id: str, access: dict):
        try:
            operation = (await self._data_svc.locate('operations', {'id': operation_id}))[0]
        except IndexError:
            raise JsonHttpNotFound(f'Operation not found: {operation_id}')
        if operation.match(access):
            return operation
        raise JsonHttpForbidden(f'Insufficient permissions to view operation {operation_id}')

    async def get_agent(self, access: dict, data: dict):
        agent_search = {'paw': data['paw'], **access}
        try:
            agent = (await self._data_svc.locate('agents', match=agent_search))[0]
        except IndexError:
            raise JsonHttpNotFound(f'Agent {data["paw"]} was not found.')
        return agent

    def create_secondclass_object_from_schema(self, schema: SchemaMeta, data: dict, access: BaseWorld.Access):
        obj_schema = schema()
        obj = obj_schema.load(data)
        obj.access = self._get_allowed_from_access(access)
        return obj
