from marshmallow.schema import SchemaMeta

from app.api.v2.managers.base_api_manager import BaseApiManager
from app.api.v2.responses import JsonHttpNotFound, JsonHttpForbidden, JsonHttpBadRequest
from app.objects.secondclass.c_link import LinkSchema
from app.utility.base_world import BaseWorld


class OperationApiManager(BaseApiManager):
    def __init__(self, data_svc, file_svc):
        super().__init__(data_svc=data_svc, file_svc=file_svc)

    async def get_operation_report(self, operation_id: str, access: dict):
        operation = await self.get_operation(operation_id, access)
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

        new_link = self.create_secondclass_object_from_schema(LinkSchema, link_data, access)
        if existing_link:
            operation.chain.remove(entry)
        operation.chain.append(new_link)
        return new_link.display

    async def create_potential_link(self, operation_id: str, link_data: dict, access: BaseWorld.Access):
        operation = await self.get_operation(operation_id, access)
        link_id = link_data['id']
        for entry in operation.potential_links:
            if entry.id == link_id:
                raise JsonHttpBadRequest(f'Link with given id already exists: {link_id}')
        new_link = self.create_secondclass_object_from_schema(LinkSchema, link_data, access)
        operation.potential_links.append(new_link)
        return new_link.display

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
            raise JsonHttpNotFound(f'paw {paw} was not found in potential links for Operation {operation_id}')
        return output_links

    """Object Creation Helpers"""
    async def get_operation(self, operation_id: str, access: dict):
        try:
            operation = (await self._data_svc.locate('operations', {'id': operation_id}))[0]
        except Exception:
            raise JsonHttpNotFound(f'Operation {operation_id} was not found.')
        if operation.match(access):
            return operation
        raise JsonHttpForbidden(f'Insufficient permissions to view operation {operation_id}')

    def create_secondclass_object_from_schema(self, schema: SchemaMeta, data: dict, access: BaseWorld.Access):
        obj_schema = schema()
        obj = obj_schema.load(data)
        obj.access = self._get_allowed_from_access(access)
        return obj
