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

    @aiohttp_apispec.docs(tags=['schedules'])
    @aiohttp_apispec.querystring_schema(BaseGetAllQuerySchema)
    @aiohttp_apispec.response_schema(ScheduleSchema(many=True, partial=True))
    async def get_schedules(self, request: web.Request):
        schedules = await self.get_all_objects(request)
        return web.json_response(schedules)

    @aiohttp_apispec.docs(tags=['schedules'])
    @aiohttp_apispec.querystring_schema(BaseGetOneQuerySchema)
    @aiohttp_apispec.response_schema(ScheduleSchema(partial=True))
    async def get_schedule_by_name(self, request: web.Request):
        schedule = await self.get_object(request)
        return web.json_response(schedule)

    @aiohttp_apispec.docs(tags=['schedules'])
    @aiohttp_apispec.request_schema(ScheduleSchema)
    @aiohttp_apispec.response_schema(ScheduleSchema)
    async def create_schedule(self, request: web.Request):
        schedule = await self.create_object(request)
        return web.json_response(schedule.display)

    @aiohttp_apispec.docs(tags=['schedules'])
    @aiohttp_apispec.request_schema(ScheduleSchema(partial=True))
    @aiohttp_apispec.response_schema(ScheduleSchema)
    async def update_schedule(self, request: web.Request):
        schedule = await self.update_object(request)
        return web.json_response(schedule.display)

    @aiohttp_apispec.docs(tags=['schedules'])
    @aiohttp_apispec.request_schema(ScheduleSchema(partial=True))
    @aiohttp_apispec.response_schema(ScheduleSchema)
    async def create_or_update_schedule(self, request: web.Request):
        schedule = await self.create_or_update_object(request)
        return web.json_response(schedule.display)

    @aiohttp_apispec.docs(tags=['schedules'])
    @aiohttp_apispec.response_schema(ScheduleSchema)
    async def delete_schedule(self, request: web.Request):
        await self.delete_object(request)
        return web.HTTPNoContent()
