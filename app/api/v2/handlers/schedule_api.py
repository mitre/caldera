import aiohttp_apispec
from aiohttp import web

from app.api.v2.handlers.base_object_api import BaseObjectApi
from app.api.v2.managers.schedule_api_manager import ScheduleApiManager
from app.api.v2.responses import JsonHttpForbidden
from app.api.v2.schemas.base_schemas import BaseGetAllQuerySchema, BaseGetOneQuerySchema
from app.objects.c_schedule import Schedule, ScheduleSchema
from app.utility.base_world import BaseWorld


class ScheduleApi(BaseObjectApi):
    def __init__(self, services):
        super().__init__(description='schedule', obj_class=Schedule, schema=ScheduleSchema, ram_key='schedules',
                         id_property='id', auth_svc=services['auth_svc'])
        self._api_manager = ScheduleApiManager(services)
        self._rest_svc = services['rest_svc']

    def add_routes(self, app: web.Application):
        router = app.router
        router.add_get('/schedules', self.get_schedules)
        router.add_get('/schedules/{id}', self.get_schedule_by_id)
        router.add_post('/schedules', self.create_schedule)
        router.add_patch('/schedules/{id}', self.update_schedule)
        router.add_put('/schedules/{id}', self.create_or_update_schedule)
        router.add_delete('/schedules/{id}', self.delete_schedule)

    @aiohttp_apispec.docs(tags=['schedules'], summary='Retrieve Schedules', description='Returns all stored schedules.')
    @aiohttp_apispec.querystring_schema(BaseGetAllQuerySchema)
    @aiohttp_apispec.response_schema(ScheduleSchema(many=True, partial=True),
                                     description='The response is a list of all scheduled operations.')
    async def get_schedules(self, request: web.Request):
        schedules = await self.get_all_objects(request)
        return web.json_response(schedules)

    @aiohttp_apispec.docs(tags=['schedules'], summary='Retrieve Schedule',
                          parameters=[{
                              'in': 'path',
                              'name': 'id',
                              'schema': {'type': 'string'},
                              'required': 'true',
                              'description': 'UUID of the Schedule to be retrieved.'
                          }],
                          description='Retrieves Schedule by UUID, as specified by {id} in the request url.')
    @aiohttp_apispec.querystring_schema(BaseGetOneQuerySchema)
    @aiohttp_apispec.response_schema(ScheduleSchema(partial=True),
                                     description='The response is a single dumped Scheduled object.')
    async def get_schedule_by_id(self, request: web.Request):
        schedule = await self.get_object(request)
        return web.json_response(schedule)

    @aiohttp_apispec.docs(tags=['schedules'], summary='Create Schedule',
                          description='Use fields from the ScheduleSchema in the request body '
                                      'to create a new Schedule.')
    @aiohttp_apispec.request_schema(ScheduleSchema())
    @aiohttp_apispec.response_schema(ScheduleSchema, description='The response is a dump of the newly '
                                                                 'created Schedule object.')
    async def create_schedule(self, request: web.Request):
        schedule = await self.create_object(request)
        return web.json_response(schedule.display)

    @aiohttp_apispec.docs(tags=['schedules'], summary='Update Schedule',
                          parameters=[{
                              'in': 'path',
                              'name': 'id',
                              'schema': {'type': 'string'},
                              'required': 'true',
                              'description': 'UUID of the Schedule to be retrieved.'
                          }],
                          description='Use fields from the ScheduleSchema in the request body '
                                      'to update an existing Schedule.')
    @aiohttp_apispec.request_schema(ScheduleSchema(partial=True, only=['schedule', 'task.autonomous', 'task.state',
                                                                       'task.obfuscator']))
    @aiohttp_apispec.response_schema(ScheduleSchema, description='The response is a dump of the newly '
                                                                 'updated Schedule object.')
    async def update_schedule(self, request: web.Request):
        schedule = await self.update_object(request)
        return web.json_response(schedule.display)

    @aiohttp_apispec.docs(tags=['schedules'], summary='Replace Schedule',
                          parameters=[{
                              'in': 'path',
                              'name': 'id',
                              'schema': {'type': 'string'},
                              'required': 'true',
                              'description': 'UUID of the Schedule to be retrieved.'
                          }],
                          description='Use fields from the ScheduleSchema in the request body '
                                      'to replace an existing Schedule or create a new Schedule.')
    @aiohttp_apispec.request_schema(ScheduleSchema(partial=True, exclude=['id']))
    @aiohttp_apispec.response_schema(ScheduleSchema, description='The response is a dump of the newly '
                                                                 'replaced Schedule object.')
    async def create_or_update_schedule(self, request: web.Request):
        schedule = await self.create_or_update_object(request)
        return web.json_response(schedule.display)

    @aiohttp_apispec.docs(tags=['schedules'], summary='Delete Schedule',
                          parameters=[{
                              'in': 'path',
                              'name': 'id',
                              'schema': {'type': 'string'},
                              'required': 'true',
                              'description': 'UUID of the Schedule to be retrieved.'
                          }],
                          description='Deletes a Schedule object from the data service.')
    @aiohttp_apispec.response_schema(ScheduleSchema,
                                     description='Returns HTTP 204 No Content status code if '
                                                 'Schedule is deleted successfully.')
    async def delete_schedule(self, request: web.Request):
        await self.delete_object(request)
        return web.HTTPNoContent()

    '''Overridden Methods'''

    async def create_object(self, request: web.Request):
        data = await request.json()
        await self._error_if_object_with_id_exists(data.get(self.id_property))
        access = await self.get_request_permissions(request)
        return await self._create_and_dump_schedule(data, access)

    async def create_or_update_object(self, request: web.Request):
        data, access, obj_id, query, search = await self._parse_common_data_from_request(request)
        matched_obj = self._api_manager.find_object(self.ram_key, query)
        if matched_obj and matched_obj.access not in access['access']:
            raise JsonHttpForbidden(f'Cannot update Schedule {self.id} due to insufficient permissions: {obj_id}')
        return await self._create_and_dump_schedule(data, access)

    '''Private Methods'''

    async def _create_and_dump_schedule(self, data: dict, access: BaseWorld.Access):
        operation = await self._api_manager.validate_and_setup_task(data['task'], access)
        data['task'] = operation.schema.dump(operation)
        return self._api_manager.create_object_from_schema(self.schema, data, access)
