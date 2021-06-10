import aiohttp_apispec
from aiohttp import web

from app.api.v2.handlers.base_object_api import BaseObjectApi
from app.api.v2.managers.base_api_manager import BaseApiManager
from app.api.v2.schemas.base_schemas import BaseGetAllQuerySchema, BaseGetOneQuerySchema
from app.objects.c_objective import Objective, ObjectiveSchema


class ObjectiveApi(BaseObjectApi):
    def __init__(self, services):
        super().__init__(description='objective', obj_class=Objective, schema=ObjectiveSchema, ram_key='objectives',
                         id_property='id', auth_svc=services['auth_svc'])
        self._api_manager = BaseApiManager(data_svc=services['data_svc'], file_svc=services['file_svc'])

    def add_routes(self, app: web.Application):
        router = app.router
        router.add_get('/objectives', self.get_objectives)
        router.add_get('/objectives/{id}', self.get_objective_by_id)
        router.add_post('/objectives', self.create_objective)
        router.add_patch('/objectives/{id}', self.update_objective)
        router.add_put('/objectives/{id}', self.create_or_update_objective)

    @aiohttp_apispec.docs(tags=['objectives'])
    @aiohttp_apispec.querystring_schema(BaseGetAllQuerySchema)
    @aiohttp_apispec.response_schema(ObjectiveSchema(many=True, partial=True))
    async def get_objectives(self, request: web.Request):
        objectives = await self.get_all_objects(request)
        return web.json_response(objectives)

    @aiohttp_apispec.docs(tags=['objectives'])
    @aiohttp_apispec.querystring_schema(BaseGetOneQuerySchema)
    @aiohttp_apispec.response_schema(ObjectiveSchema(partial=True))
    async def get_objective_by_id(self, request: web.Request):
        objective = await self.get_object(request)
        return web.json_response(objective)

    @aiohttp_apispec.docs(tags=['objectives'])
    @aiohttp_apispec.request_schema(ObjectiveSchema)
    @aiohttp_apispec.response_schema(ObjectiveSchema)
    async def create_objective(self, request: web.Request):
        objective = await self.create_on_disk_object(request)
        return web.json_response(objective.display)

    @aiohttp_apispec.docs(tags=['objectives'])
    @aiohttp_apispec.request_schema(ObjectiveSchema(partial=True))
    @aiohttp_apispec.response_schema(ObjectiveSchema)
    async def update_objective(self, request: web.Request):
        objective = await self.update_on_disk_object(request)
        return web.json_response(objective.display)

    @aiohttp_apispec.docs(tags=['objectives'])
    @aiohttp_apispec.request_schema(ObjectiveSchema(partial=True))
    @aiohttp_apispec.response_schema(ObjectiveSchema)
    async def create_or_update_objective(self, request: web.Request):
        objective = await self.create_or_update_on_disk_object(request)
        return web.json_response(objective.display)
