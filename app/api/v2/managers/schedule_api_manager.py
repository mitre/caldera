from app.api.v2.managers.base_api_manager import BaseApiManager
from app.objects.c_operation import OperationSchema
from app.utility.base_world import BaseWorld

from marshmallow.schema import SchemaMeta


class ScheduleApiManager(BaseApiManager):
    def __init__(self, data_svc, file_svc):
        super().__init__(data_svc=data_svc, file_svc=file_svc)

    def create_object_from_schema(self, schema: SchemaMeta, data: dict, access: BaseWorld.Access):
        operation = OperationSchema().load(data=data["task"])
        data['task'] = operation
        obj_schema = schema()
        obj = obj_schema.load(data)
        obj.access = self._get_allowed_from_access(access)
        obj.store(self._data_svc.ram)
        return obj
