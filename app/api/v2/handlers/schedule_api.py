import aiohttp_apispec
from aiohttp import web

from app.api.v2.handlers.base_object_api import BaseObjectApi
from app.api.v2.managers.base_api_manager import BaseApiManager
from app.api.v2.schemas.base_schemas import BaseGetAllQuerySchema, BaseGetOneQuerySchema
from app.objects.c_schedule import Schedule, ScheduleSchema


class ScheduleApi(BaseObjectApi):
    def __init__(self, services):
        super().__init__(description='schedule', obj_class=Schedule, schema=ScheduleSchema, ram_key='schedules',
                         id_property='name', auth_svc=services['auth_svc'])
        self._api_manager = BaseApiManager(data_svc=services['data_svc'], file_svc=services['file_svc'])

    def add_routes(self, app: web.Application):
        router = app.router
        router.add_get('/schedules', self.get_schedules)
        router.add_get('/schedules/{name}', self.get_schedule_by_name)
        router.add_post('/schedules', self.create_schedule)
        router.add_patch('/schedules/{name}', self.update_schedule)
        router.add_put('/schedules/{name}', self.create_or_update_schedule)
        router.add_delete('/schedules/{name}', self.delete_schedule)

    @aiohttp_apispec.docs(tags=['schedules'], summary='Retrieve Schedules', description='Returns all stored schedules.')
    @aiohttp_apispec.querystring_schema(BaseGetAllQuerySchema)
    @aiohttp_apispec.response_schema(ScheduleSchema(many=True, partial=True),
                                     description='The response is a list of all the scheduled operations that have not '
                                                 'been completed.')
    async def get_schedules(self, request: web.Request):
        schedules = await self.get_all_objects(request)
        return web.json_response(schedules)

    @aiohttp_apispec.docs(tags=['schedules'], summary='Retrieve Schedule',
                          parameters=[{
                              'in': 'path',
                              'name': 'name',
                              'schema': {'type': 'string'},
                              'required': 'true',
                              'description': 'Name of the Schedule to be retrieved.'
                          }],
                          description='Retrieves Schedule by name, as specified by {name} in the request url.')
    @aiohttp_apispec.querystring_schema(BaseGetOneQuerySchema)
    @aiohttp_apispec.response_schema(ScheduleSchema(partial=True))
    async def get_schedule_by_name(self, request: web.Request):
        schedule = await self.get_object(request)
        return web.json_response(schedule)

    @aiohttp_apispec.docs(tags=['schedules'], summary='Create Schedule',
                          description='Use fields from the ScheduleSchema in the request body '
                                      'to create a new Schedule.')
    @aiohttp_apispec.request_schema(ScheduleSchema)
    @aiohttp_apispec.response_schema(ScheduleSchema, description='The response is a dump of the newly '
                                                                 'created Schedule object.')
    async def create_schedule(self, request: web.Request):
        schedule = await self.create_object(request)
        return web.json_response(schedule.display)

    @aiohttp_apispec.docs(tags=['schedules'], summary='Update Schedule',
                          parameters=[{
                              'in': 'path',
                              'name': 'name',
                              'schema': {'type': 'string'},
                              'required': 'true',
                              'description': 'Name of the Schedule to be updated.'
                          }],
                          description='Use fields from the ScheduleSchema in the request body '
                                      'to update an existing Schedule.')
    @aiohttp_apispec.request_schema(ScheduleSchema(partial=True, only=['schedule']))
    @aiohttp_apispec.response_schema(ScheduleSchema, description='The response is a dump of the newly '
                                                                 'updated Schedule object.')
    async def update_schedule(self, request: web.Request):
        schedule = await self.update_object(request)
        return web.json_response(schedule.display)

    @aiohttp_apispec.docs(tags=['schedules'], summary='Replace Schedule',
                          parameters=[{
                              'in': 'path',
                              'name': 'name',
                              'schema': {'type': 'string'},
                              'required': 'true',
                              'description': 'Name of the Schedule to be replaced.'
                          }],
                          description='Use fields from the ScheduleSchema in the request body '
                                      'to replace an existing Schedule or create a new Schedule.')
    @aiohttp_apispec.request_schema(ScheduleSchema(partial=True))
    @aiohttp_apispec.response_schema(ScheduleSchema, description='The response is a dump of the newly '
                                                                 'Replaced Schedule object.')
    async def create_or_update_schedule(self, request: web.Request):
        schedule = await self.create_or_update_object(request)
        return web.json_response(schedule.display)

    @aiohttp_apispec.docs(tags=['schedules'], summary='Delete Schedule',
                          parameters=[{
                              'in': 'path',
                              'name': 'name',
                              'schema': {'type': 'string'},
                              'required': 'true',
                              'description': 'Name of the Schedule to be deleted.'
                          }],
                          description='Deletes a Schedule object from the data service.')
    @aiohttp_apispec.response_schema(ScheduleSchema,
                                     description='Returns HTTP 204 No Content status code if '
                                                 'Schedule is deleted successfully.')
    async def delete_schedule(self, request: web.Request):
        await self.delete_object(request)
        return web.HTTPNoContent()
