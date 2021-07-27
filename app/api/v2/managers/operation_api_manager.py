import uuid

from app.api.v2.managers.base_api_manager import BaseApiManager
from app.api.v2.responses import JsonHttpNotFound, JsonHttpForbidden, JsonHttpBadRequest
from app.objects.secondclass.c_link import Link
from app.objects.secondclass.c_executor import Executor
from app.objects.c_ability import Ability
from app.objects.c_agent import Agent
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

    async def get_operation_links(self, operation_id: str, access: dict):
        operation = await self.get_operation_object(operation_id, access)
        links = [link.display for link in operation.chain]
        return links

    async def get_operation_link(self, operation_id: str, link_id: str, access: dict):
        operation = await self.get_operation_object(operation_id, access)
        link = self.search_operation_for_link(operation, link_id)
        return link.display

    async def update_operation_link(self, operation_id: str, link_id: str, link_data: dict, access: BaseWorld.Access):
        operation = await self.get_operation_object(operation_id, access)
        link = self.search_operation_for_link(operation, link_id)
        if link.access not in access['access']:
            raise JsonHttpForbidden(f'Cannot update link {link_id} due to insufficient permissions.')
        if link.is_finished() or link.can_ignore():
            raise JsonHttpForbidden(f'Cannot update a finished link: {link_id}')
        if link_data.get('status'):
            link.status = link_data.get('status')
        if link_data.get('command'):
            link.command = link_data.get('command')
            command_str = self._decode_string(link_data.get('command'))
            link.executor.command = command_str
        return link.display

    async def create_potential_link(self, operation_id: str, data: dict, access: BaseWorld.Access):
        self.validate_link_data(data)
        operation = await self.get_operation_object(operation_id, access)
        link_id = data.get('id', str(uuid.uuid4()))
        if operation.has_link(link_id):
            raise JsonHttpForbidden(f'Operation {operation_id} already has link {link_id}')
        agent = await self.get_agent(access, data)
        if data['executor']['name'] not in agent.executors:
            raise JsonHttpBadRequest(f'Agent {agent.paw} missing specified executor')
        encoded_command = self._encode_string(data['executor']['command'])
        executor = self.build_executor(data=data.pop('executor', {}), agent=agent)
        ability = self.build_ability(data=data.pop('ability', {}), executor=executor)
        link = Link.load(dict(command=encoded_command, paw=agent.paw, ability=ability, executor=executor,
                              status=operation.link_status(), score=data.get('score', 0), jitter=data.get('jitter', 0),
                              cleanup=data.get('cleanup', 0), id=link_id, pin=data.get('pin', 0),
                              host=agent.host, deadman=data.get('deadman', False), used=data.get('used', []),
                              relationships=data.get('relationships', [])))
        link.replace_origin_link_id()
        await operation.apply(link)
        return link.display

    async def get_potential_links(self, operation_id: str, access: dict, paw: str = None):
        operation = await self.get_operation_object(operation_id, access)
        if operation.finish:
            return []
        if paw:
            agent = next((a for a in operation.agents if a.paw == paw), None)
            if not agent:
                raise JsonHttpNotFound(f'Agent not found: {paw}')
        agents = await self.services['data_svc'].locate('agents', match=dict(paw=paw)) if paw else operation.agents
        potential_abilities = await self.services['rest_svc'].build_potential_abilities(operation)
        operation.potential_links = await self.services['rest_svc'].build_potential_links(operation, agents, potential_abilities)
        potential_links = [potential_link.display for potential_link in operation.potential_links]
        return potential_links

    """Object Creation Helpers"""
    async def get_operation_object(self, operation_id: str, access: dict):
        try:
            operation = (await self._data_svc.locate('operations', {'id': operation_id}))[0]
        except IndexError:
            raise JsonHttpNotFound(f'Operation not found: {operation_id}')
        if operation.match(access):
            return operation
        raise JsonHttpForbidden(f'Insufficient permissions to view operation {operation_id}')

    def search_operation_for_link(self, operation: Operation, link_id: str):
        for link in operation.chain:
            if link.id == link_id:
                return link
        raise JsonHttpNotFound(f'Link {link_id} was not found in Operation {operation.id}')

    def validate_link_data(self, link_data: dict):
        if not link_data.get('executor'):
            raise JsonHttpBadRequest('\'executor\' is a required field for link creation.')
        if not link_data['executor'].get('name'):
            raise JsonHttpBadRequest('\'name\' is a required field for link executor.')
        if not link_data['executor'].get('command'):
            raise JsonHttpBadRequest('\'command\' is a required field for link executor.')
        if not link_data.get('paw'):
            raise JsonHttpBadRequest('\'paw\' is a required field for link creation.')

    async def get_agent(self, access: dict, data: dict):
        agent_search = {'paw': data['paw'], **access}
        try:
            agent = (await self._data_svc.locate('agents', match=agent_search))[0]
        except IndexError:
            raise JsonHttpNotFound(f'Agent {data["paw"]} was not found.')
        return agent

    def build_executor(self, data: dict, agent: Agent):
        executor = Executor(name=data['name'],
                            platform=agent.platform,
                            command=data['command'],
                            code=data.get('code', None),
                            language=data.get('language', None),
                            build_target=data.get('build_target', None),
                            payloads=data.get('payloads', None),
                            uploads=data.get('uploads', None),
                            timeout=data.get('timeout', 60),
                            parsers=data.get('parsers', None),
                            cleanup=data.get('cleanup', None),
                            variations=data.get('variations', None),
                            additional_info=data.get('additional_info', None))
        return executor

    def build_ability(self, data: dict, executor: Executor):
        ability = Ability(ability_id=data.get('ability_id', str(uuid.uuid4())),
                          tactic=data.get('tactic', 'auto-generated'),
                          technique_id=data.get('technique_id', 'auto-generated'),
                          technique_name=data.get('technique_name', 'auto-generated'),
                          name=data.get('name', 'Manual Command'),
                          description=data.get('description', 'Manual command ability'),
                          executors=[executor],
                          requirements=data.get('requirements', None),
                          privilege=data.get('privilege', None),
                          repeatable=data.get('repeatable', None),
                          buckets=data.get('buckets', None),
                          access=data.get('access', None),
                          additional_info=data.get('additional_info', {}),
                          tags=data.get('tags', None),
                          singleton=())
        return ability
