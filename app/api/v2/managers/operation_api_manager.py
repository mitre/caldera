from app.api.v2.managers.base_api_manager import BaseApiManager


class OperationApiManager(BaseApiManager):
    def __init__(self, data_svc, file_svc):
        super().__init__(data_svc=data_svc, file_svc=file_svc)

    async def get_operation_report(self, operation_id: str):
        operation = (await self._data_svc.locate('operations', {'id': operation_id}))[0]
        report = await operation.report(file_svc=self._file_svc, data_svc=self._data_svc)

        return report
