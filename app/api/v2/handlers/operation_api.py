# import aiohttp_apispec
from aiohttp import web

from app.api.v2.handlers.base_object_api import BaseObjectApi
from app.api.v2.managers.base_api_manager import BaseApiManager
# from app.api.v2.schemas.base_schemas import BaseGetAllQuerySchema, BaseGetOneQuerySchema
from app.objects.c_operation import Operation, OperationSchema


class OperationApi(BaseObjectApi):
    def __init__(self, services):
        super().__init__(description='operation', obj_class=Operation, schema=OperationSchema, ram_key='operations',
                         id_property='id', auth_svc=services['auth_svc'])
        self._api_manager = BaseApiManager(data_svc=services['data_svc'], file_svc=services['file_svc'])

    def add_routes(self, app: web.Application):
        router = app.router
        router.add_get('/operations', self.get_operations)
        router.add_get('/operations/{id}', self.get_operation_by_id)
        router.add_post('/operations', self.create_operation)
        router.add_put('/operations/{id}', self.create_or_update_operation)
        router.add_patch('/operations/{id}', self.update_operation)
        router.add_delete('/operations/{id}', self.delete_operation)

        router.add_get('/operations/{id}/report', self.get_operation_report)

        router.add_get('/operations/{id}/links', self.get_operation_links)
        router.add_get('/operations/{id}/links/{id}', self.get_operation_link)
        router.add_put('/operations/{id}/links/{id}', self.create_or_update_operation_link)

        router.add_post('/operations/{id}/potential-links', self.create_potential_links)
        router.add_get('/operations/{id}/potential-links', self.get_potential_links)
        router.add_get('/operations/{id}/potential-links/{paw}', self.get_potential_link)

    def get_operations(self):
        pass

    def get_operation_by_id(self):
        pass

    def create_operation(self):
        pass

    def create_or_update_operation(self):
        pass

    def update_operation(self):
        pass

    def delete_operation(self):
        pass

    def get_operation_report(self):
        pass

    def get_operation_links(self):
        pass

    def get_operation_link(self):
        pass

    def create_or_update_operation_link(self):
        pass

    def create_potential_links(self):
        pass

    def get_potential_links(self):
        pass

    def get_potential_link(self):
        pass
