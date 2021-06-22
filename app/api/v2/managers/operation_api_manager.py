from app.api.v2.managers.base_api_manager import BaseApiManager


class OperationApiManager(BaseApiManager):
    def __init__(self, data_svc, file_svc):
        super().__init__(data_svc=data_svc, file_svc=file_svc)

    async def get_operation_report(self, operation_id: str):
        operation = (await self._data_svc.locate('operations', {'id': operation_id}))[0]
        report = await operation.report(file_svc=self._file_svc, data_svc=self._data_svc)

        return report

    async def get_operation_links(self, operation_id: str):
        operation = (await self._data_svc.locate('operations', {'id': operation_id}))[0]
        links = [link.display for link in operation.chain]

        return links

    async def get_operation_link(self, operation_id: str, link_id: str):
        operation = (await self._data_svc.locate('operations', {'id': operation_id}))[0]

        for link in operation.chain:
            if link.id == link_id:
                return link.display
        return None

    async def get_potential_links(self, operation_id: str):
        operation = (await self._data_svc.locate('operations', {'id': operation_id}))[0]
        potential_links = [potential_link.display for potential_link in operation.potential_links]

        return potential_links

    async def get_potential_link(self, operation_id: str, paw: str):
        operation = (await self._data_svc.locate('operations', {'id': operation_id}))[0]

        for link in operation.potential_links:
            if link.paw == paw:
                return link.display
        return None
