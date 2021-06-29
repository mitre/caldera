import aiohttp_apispec
from aiohttp import web

from app.api.v2.handlers.base_object_api import BaseObjectApi
from app.api.v2.managers.fact_api_manager import FactApiManager
from app.api.v2.schemas.base_schemas import BaseGetAllQuerySchema
from app.objects.secondclass.c_fact import Fact, FactSchema, OriginType, wildcard_string
from app.objects.secondclass.c_relationship import Relationship, RelationshipSchema

class AdversaryApi(BaseObjectApi):
    def __init__(self, services):
        super().__init__(description='adversary', obj_class=Fact, schema=FactSchema, ram_key='adversaries',
                         id_property='adversary_id', auth_svc=services['auth_svc'])
        self._api_manager = FactApiManager(data_svc=services['data_svc'], file_svc=services['file_svc'],
                                           knowledge_svc=services['knowledge_svc'])

    def add_routes(self, app: web.Application):
        router = app.router
        router.add_get('/facts', self.get_facts)
        router.add_get('/relationships', self.get_relationships)
        router.add_post('/facts', self.add_facts)
        router.add_post('/relationships', self.add_relationships)
        router.add_delete('/facts', self.delete_facts)
        router.add_delete('/relationships', self.delete_relationships)

    @aiohttp_apispec.docs(tags=['facts'])
    @aiohttp_apispec.querystring_schema(BaseGetAllQuerySchema)
    @aiohttp_apispec.response_schema(FactSchema(many=True, partial=True))
    async def get_facts(self, request: web.Request):
        knowledge_svc_handle = self._api_manager._knowledge_svc
        fact_data = request.content
        try:
            new_fact = Fact.load(fact_data)
            if 'source' not in fact_data:
                new_fact.source = wildcard_string
            new_fact.source_type = OriginType.USER.name
            await knowledge_svc_handle.add_fact(new_fact)
            store = await knowledge_svc_handle.get_facts(criteria=dict(trait=fact_data['trait'],
                                                                       value=fact_data['value'],
                                                                       source=wildcard_string,
                                                                       source_type=OriginType.USER.name))
            return [x.display for x in store]
        except Exception as e:
            self.log.warning(f'Encountered issue saving fact {fact_data} - {e}')

    @aiohttp_apispec.docs(tags=['facts', 'relationships'])
    @aiohttp_apispec.querystring_schema(BaseGetAllQuerySchema)
    @aiohttp_apispec.response_schema(RelationshipSchema(many=True, partial=True))
    async def get_relationships(self, request: web.Request):
        pass

    @aiohttp_apispec.docs(tags=['facts'])
    @aiohttp_apispec.request_schema(FactSchema)
    @aiohttp_apispec.request_schema(FactSchema)
    async def add_facts(self, request: web.Request):
        pass

    @aiohttp_apispec.docs(tags=['facts', 'relationships'])
    @aiohttp_apispec.request_schema(RelationshipSchema)
    @aiohttp_apispec.request_schema(RelationshipSchema)
    async def add_relationships(self, request: web.Request):
        pass

    @aiohttp_apispec.docs(tags=['facts'])
    @aiohttp_apispec.response_schema(FactSchema)
    async def delete_fact(self, request: web.Request):
        pass

    @aiohttp_apispec.docs(tags=['facts', 'relationships'])
    @aiohttp_apispec.response_schema(RelationshipSchema)
    async def delete_relationship(self, request: web.Request):
        pass
