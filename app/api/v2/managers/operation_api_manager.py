from app.api.v2.managers.base_api_manager import BaseApiManager
from app.objects.secondclass.c_link import LinkSchema
from app.api.v2.responses import JsonHttpNotFound


class OperationApiManager(BaseApiManager):
    def __init__(self, data_svc, file_svc):
        super().__init__(data_svc=data_svc, file_svc=file_svc)

    async def get_operation_report(self, operation_id: str):
        try:
            operation = (await self._data_svc.locate('operations', {'id': operation_id}))[0]
        except Exception:
            raise JsonHttpNotFound(f'Operation {operation_id} was not found.')
        report = await operation.report(file_svc=self._file_svc, data_svc=self._data_svc)

        return report

    async def get_operation_links(self, operation_id: str):
        try:
            operation = (await self._data_svc.locate('operations', {'id': operation_id}))[0]
        except Exception:
            raise JsonHttpNotFound(f'Operation {operation_id} was not found.')
        links = [link.display for link in operation.chain]

        return links

    async def get_operation_link(self, operation_id: str, link_id: str):
        try:
            operation = (await self._data_svc.locate('operations', {'id': operation_id}))[0]
        except Exception:
            raise JsonHttpNotFound(f'Operation {operation_id} was not found.')

        for link in operation.chain:
            if link.id == link_id:
                return link.display
        raise JsonHttpNotFound(f'Link {link_id} was not found in Operation {operation_id}')

    async def create_or_update_operation_link(self, operation_id: str, link_id: str, data: dict):
        try:
            operation = (await self._data_svc.locate('operations', {'id': operation_id}))[0]
        except Exception:
            raise JsonHttpNotFound(f'Operation {operation_id} was not found.')

        access = None
        link = None
        for entry in operation.chain:
            if entry.id == link_id:
                link = entry
        if not link:
            raise JsonHttpNotFound(f'Link {link_id} was not found in Operation {operation_id}')

        new_link = self.create_object_from_schema(LinkSchema, data, access)
        for entry in operation.chain:
            if entry.id == link_id:
                del entry
        operation.chain.append(new_link)
        return new_link

    async def create_potential_links(self, operation_id: str, link_id: str, data: dict):
        pass

    async def get_potential_links(self, operation_id: str):
        try:
            operation = (await self._data_svc.locate('operations', {'id': operation_id}))[0]
        except Exception:
            raise JsonHttpNotFound(f'Operation {operation_id} was not found.')
        potential_links = [potential_link.display for potential_link in operation.potential_links]

        return potential_links

    async def get_potential_link(self, operation_id: str, paw: str):
        try:
            operation = (await self._data_svc.locate('operations', {'id': operation_id}))[0]
        except Exception:
            raise JsonHttpNotFound(f'Operation {operation_id} was not found.')

        for link in operation.potential_links:
            if link.paw == paw:
                return link.display
        raise JsonHttpNotFound(f'Potential link {paw} was not found in Operation {operation_id}')
