import aiohttp_apispec
from aiohttp import web

from app.api.v2.handlers.base_object_api import BaseObjectApi
from app.api.v2.managers.base_api_manager import BaseApiManager
from app.api.v2.schemas.base_schemas import BaseGetAllQuerySchema, BaseGetOneQuerySchema
from app.objects.c_planner import Planner, PlannerSchema


class PlannerApi(BaseObjectApi):
    def __init__(self, services):
        super().__init__(description='planner', obj_class=Planner, schema=PlannerSchema, ram_key='planners', id_property='planner_id',
                         auth_svc=services['auth_svc'])
        self._api_manager = BaseApiManager(data_svc=services['data_svc'], file_svc=services['file_svc'])

    def add_routes(self, app: web.Application):
        router = app.router
        router.add_get('/planners', self.get_planners)
        router.add_get('/planners/{planner_id}', self.get_planner_by_id)

    @aiohttp_apispec.docs(tags=['planners'],
                          summary='Retrieve planners',
                          description='Retrieve Caldera planners by criteria. Supply fields from the `PlannerSchema` '
                                      'to the `include` and `exclude` fields of the `BaseGetAllQuerySchema` in the '
                                      'request body to filter retrieved planners.')
    @aiohttp_apispec.querystring_schema(BaseGetAllQuerySchema)
    @aiohttp_apispec.response_schema(PlannerSchema(many=True, partial=True),
                                     description='Returns a list of matching planners in `PlannerSchema` format.')
    async def get_planners(self, request: web.Request):
        planners = await self.get_all_objects(request)
        return web.json_response(planners)

    @aiohttp_apispec.docs(tags=['planners'],
                          summary='Retrieve a planner by planner id',
                          description='Retrieve one Caldera planner based on the planner id (String `UUID`). '
                                      'Supply fields from the `PlannerSchema` to the `include` and `exclude` fields '
                                      'of the `BaseGetOneQuerySchema` in the request body to filter retrieved '
                                      'planners.',
                          parameters=[{
                              'in': 'path',
                              'name': 'planner_id',
                              'schema': {'type': 'string'},
                              'required': 'true',
                              'description': 'UUID of the Planner object to be retrieved.'
                          }])
    @aiohttp_apispec.querystring_schema(BaseGetOneQuerySchema)
    @aiohttp_apispec.response_schema(PlannerSchema(partial=True),
                                     description='Returns a planner with the specified id in `PlannerSchema` format.')
    async def get_planner_by_id(self, request: web.Request):
        planner = await self.get_object(request)
        return web.json_response(planner)
