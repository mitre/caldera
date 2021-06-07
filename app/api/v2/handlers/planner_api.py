import aiohttp_apispec
from aiohttp import web

from app.api.v2.handlers.base_api import BaseApi
from app.api.v2.managers.base_api_manager import BaseApiManager
from app.api.v2.responses import JsonHttpNotFound
from app.api.v2.schemas.base_schemas import BaseGetAllQuerySchema, BaseGetOneQuerySchema
from app.objects.c_planner import PlannerSchema


class PlannerApi(BaseApi):
    def __init__(self, services):
        super().__init__(auth_svc=services['auth_svc'])
        self._api_manager = BaseApiManager(data_svc=services['data_svc'])

    def add_routes(self, app: web.Application):
        router = app.router
        router.add_get('/planners', self.get_planners)
        router.add_get('/planners/{planner_id}', self.get_planner_by_id)

    @aiohttp_apispec.docs(tags=['planners'])
    @aiohttp_apispec.querystring_schema(BaseGetAllQuerySchema)
    @aiohttp_apispec.response_schema(PlannerSchema(many=True))
    async def get_planners(self, request: web.Request):
        sort = request['querystring'].get('sort', 'name')
        include = request['querystring'].get('include')
        exclude = request['querystring'].get('exclude')

        planners = self._api_manager.get_objects_with_filters('planners', sort=sort, include=include, exclude=exclude)
        return web.json_response(planners)

    @aiohttp_apispec.docs(tags=['planners'])
    @aiohttp_apispec.querystring_schema(BaseGetOneQuerySchema)
    @aiohttp_apispec.response_schema(PlannerSchema)
    async def get_planner_by_id(self, request: web.Request):
        planner_id = request.match_info['planner_id']
        include = request['querystring'].get('include')
        exclude = request['querystring'].get('exclude')

        search = dict(planner_id=planner_id)

        planner = self._api_manager.get_object_with_filters('planners', search=search, include=include, exclude=exclude)
        if not planner:
            raise JsonHttpNotFound(f'Planner not found: {planner_id}')

        return web.json_response(planner)
