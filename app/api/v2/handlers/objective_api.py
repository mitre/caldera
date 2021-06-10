import aiohttp_apispec
from aiohttp import web

from app.api.v2.handlers.base_api import BaseApi
from app.api.v2.managers.base_api_manager import BaseApiManager
from app.api.v2.responses import JsonHttpNotFound, JsonHttpForbidden
from app.api.v2.schemas.base_schemas import BaseGetAllQuerySchema, BaseGetOneQuerySchema
from app.objects.c_objective import ObjectiveSchema


class ObjectiveApi(BaseApi):
    def __init__(self, services):
        super().__init__(auth_svc=services['auth_svc'])
        self._api_manager = BaseApiManager(data_svc=services['data_svc'], file_svc=services['file_svc'])

    def add_routes(self, app: web.Application):
        router = app.router
        router.add_get('/objectives', self.get_objectives)
        router.add_get('/objectives/{objective_id}', self.get_objective_by_id)
        router.add_post('/objectives', self.create_objective)
        router.add_patch('/objectives/{objective_id}', self.update_objective)
        router.add_put('/objectives/{objective_id}', self.create_or_update_objective)

    @aiohttp_apispec.docs(tags=['objectives'])
    @aiohttp_apispec.querystring_schema(BaseGetAllQuerySchema)
    @aiohttp_apispec.response_schema(ObjectiveSchema(many=True, partial=True))
    async def get_objectives(self, request: web.Request):
        sort = request['querystring'].get('sort', 'name')
        include = request['querystring'].get('include')
        exclude = request['querystring'].get('exclude')

        access = await self.get_request_permissions(request)

        objectives = self._api_manager.find_and_dump_objects('objectives', access, sort, include, exclude)
        return web.json_response(objectives)

    @aiohttp_apispec.docs(tags=['objectives'])
    @aiohttp_apispec.querystring_schema(BaseGetOneQuerySchema)
    @aiohttp_apispec.response_schema(ObjectiveSchema(partial=True))
    async def get_objective_by_id(self, request: web.Request):
        objective_id = request.match_info['objective_id']
        include = request['querystring'].get('include')
        exclude = request['querystring'].get('exclude')

        access = await self.get_request_permissions(request)
        query = dict(id=objective_id)
        search = {**query, **access}

        objective = self._api_manager.find_and_dump_object('objectives', search, include, exclude)
        if not objective:
            raise JsonHttpNotFound(f'Objective not found: {objective_id}')

        return web.json_response(objective)

    @aiohttp_apispec.docs(tags=['objectives'])
    @aiohttp_apispec.request_schema(ObjectiveSchema)
    @aiohttp_apispec.response_schema(ObjectiveSchema)
    async def create_objective(self, request: web.Request):
        objective_data = await request.json()
        objective = self._api_manager.create_object_from_schema(ObjectiveSchema, objective_data)
        return web.json_response(objective.display)

    @aiohttp_apispec.docs(tags=['objectives'])
    @aiohttp_apispec.request_schema(ObjectiveSchema(partial=True))
    @aiohttp_apispec.response_schema(ObjectiveSchema)
    async def update_objective(self, request: web.Request):
        objective_id = request.match_info['objective_id']
        objective_data = await request.json()
        objective_data['id'] = objective_id

        access = await self.get_request_permissions(request)
        query = dict(id=objective_id)
        search = {**query, **access}

        objective = self._api_manager.find_and_update_object('objectives', objective_data, search)
        if not objective:
            raise JsonHttpNotFound(f'Objective not found: {objective_id}')

        return web.json_response(objective.display)

    @aiohttp_apispec.docs(tags=['objectives'])
    @aiohttp_apispec.request_schema(ObjectiveSchema(partial=True))
    @aiohttp_apispec.response_schema(ObjectiveSchema)
    async def create_or_update_objective(self, request: web.Request):
        objective_id = request.match_info['objective_id']
        objective_data = await request.json()
        objective_data['id'] = objective_id

        access = await self.get_request_permissions(request)
        query = dict(id=objective_id)
        search = {**query, **access}

        search_objective = next(self._api_manager.find_objects('objectives', search), None)
        if search_objective is not None and search_objective.access not in access['access']:
            raise JsonHttpForbidden(f'Cannot update objectives due to insufficient permissions: {objective_id}')

        objective = self._api_manager.create_object_from_schema(ObjectiveSchema, objective_data)
        return web.json_response(objective.display)
