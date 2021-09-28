import aiohttp_apispec
from aiohttp import web

from app.api.v2.handlers.base_object_api import BaseObjectApi
from app.api.v2.managers.fact_api_manager import FactApiManager
from app.api.v2.responses import JsonHttpBadRequest
from app.api.v2.schemas.base_schemas import BaseGetAllQuerySchema
from app.objects.secondclass.c_fact import Fact, FactSchema, OriginType, WILDCARD_STRING, FactUpdateRequestSchema
from app.objects.secondclass.c_relationship import Relationship, RelationshipSchema, RelationshipUpdateSchema


class FactApi(BaseObjectApi):
    def __init__(self, services):
        super().__init__(description='adversary', obj_class=Fact, schema=FactSchema, ram_key='facts',
                         id_property='adversary_id', auth_svc=services['auth_svc'])
        self._api_manager = FactApiManager(data_svc=services['data_svc'], file_svc=services['file_svc'],
                                           knowledge_svc=services['knowledge_svc'])

    def add_routes(self, app: web.Application):
        router = app.router
        router.add_post('/fetch-facts', self.get_facts)
        router.add_post('/fetch-relationships', self.get_relationships)
        router.add_post('/create-facts', self.add_facts)
        router.add_post('/create-relationships', self.add_relationships)
        router.add_delete('/facts', self.delete_facts)
        router.add_delete('/relationships', self.delete_relationships)
        router.add_patch('/facts', self.update_facts)
        router.add_patch('/relationships', self.update_relationships)

    @aiohttp_apispec.docs(tags=['facts'])
    @aiohttp_apispec.querystring_schema(BaseGetAllQuerySchema)
    @aiohttp_apispec.response_schema(FactSchema(many=True, partial=True))
    @aiohttp_apispec.request_schema(FactSchema)
    async def get_facts(self, request: web.Request):
        knowledge_svc_handle = self._api_manager.knowledge_svc
        fact_data = await self._api_manager.extract_data(request)
        try:
            store = await knowledge_svc_handle.get_facts(criteria=fact_data)
            resp = await self._api_manager.verify_fact_integrity(store)
            return web.json_response(dict(found=resp))
        except Exception as e:
            error_msg = f'Encountered issue retrieving fact {fact_data} - {e}'
            self.log.warning(error_msg)
            raise JsonHttpBadRequest(error_msg)

    @aiohttp_apispec.docs(tags=['relationships'])
    @aiohttp_apispec.querystring_schema(BaseGetAllQuerySchema)
    @aiohttp_apispec.response_schema(RelationshipSchema(many=True, partial=True))
    @aiohttp_apispec.request_schema(RelationshipSchema)
    async def get_relationships(self, request: web.Request):
        knowledge_svc_handle = self._api_manager.knowledge_svc
        relationship_data = await self._api_manager.extract_data(request)
        try:
            store = await knowledge_svc_handle.get_relationships(criteria=relationship_data)
            resp = await self._api_manager.verify_relationship_integrity(store)
            return web.json_response(dict(found=resp))
        except Exception as e:
            error_msg = f'Encountered issue retrieving relationship {relationship_data} - {e}'
            self.log.warning(error_msg)
            raise JsonHttpBadRequest(error_msg)

    @aiohttp_apispec.docs(tags=['facts'])
    @aiohttp_apispec.request_schema(FactSchema)
    @aiohttp_apispec.response_schema(FactSchema)
    async def add_facts(self, request: web.Request):
        knowledge_svc_handle = self._api_manager.knowledge_svc
        fact_data = await self._api_manager.extract_data(request)
        try:
            new_fact = Fact.load(fact_data)
            if 'source' not in fact_data:
                new_fact.source = WILDCARD_STRING
            new_fact.source_type = OriginType.USER.name
            await knowledge_svc_handle.add_fact(new_fact)
            store = await knowledge_svc_handle.get_facts(criteria=dict(trait=new_fact.trait,
                                                                       value=new_fact.value,
                                                                       source=WILDCARD_STRING,
                                                                       source_type=OriginType.USER.name))
            resp = await self._api_manager.verify_fact_integrity(store)
            return web.json_response(dict(added=resp))
        except Exception as e:
            error_msg = f'Encountered issue saving fact {fact_data} - {e}'
            self.log.warning(error_msg)
            raise JsonHttpBadRequest(error_msg)

    @aiohttp_apispec.docs(tags=['relationships'])
    @aiohttp_apispec.request_schema(RelationshipSchema)
    @aiohttp_apispec.response_schema(RelationshipSchema)
    async def add_relationships(self, request: web.Request):
        knowledge_svc_handle = self._api_manager.knowledge_svc
        relationship_data = await self._api_manager.extract_data(request)
        try:
            origin_target = WILDCARD_STRING
            new_relationship = Relationship.load(relationship_data)
            if 'origin' in relationship_data:
                origin_target = relationship_data['origin']
            else:
                new_relationship.origin = origin_target
            shorthand = new_relationship.shorthand
            new_relationship.source.relationships = [shorthand]
            new_relationship.source.source = origin_target
            new_relationship.source.source_type = OriginType.USER.name
            if 'target' in relationship_data:
                new_relationship.target.source = origin_target
                new_relationship.target.source_type = OriginType.USER.name
                new_relationship.target.relationships = [shorthand]
                await knowledge_svc_handle.add_fact(new_relationship.target)
            await knowledge_svc_handle.add_fact(new_relationship.source)
            await knowledge_svc_handle.add_relationship(new_relationship)

            store = await knowledge_svc_handle.get_relationships(
                criteria=dict(source=new_relationship.source,
                              edge=new_relationship.edge if 'edge' in relationship_data else None,
                              target=new_relationship.target if 'target' in relationship_data else None,
                              origin=origin_target))
            resp = await self._api_manager.verify_relationship_integrity(store)
            return web.json_response(dict(added=resp))
        except Exception as e:
            error_msg = f'Encountered issue saving relationship {relationship_data} - {e}'
            self.log.warning(error_msg)
            raise JsonHttpBadRequest(error_msg)

    @aiohttp_apispec.docs(tags=['facts'])
    @aiohttp_apispec.response_schema(FactSchema)
    async def delete_facts(self, request: web.Request):
        knowledge_svc_handle = self._api_manager.knowledge_svc
        fact_data = await self._api_manager.extract_data(request)
        if fact_data:
            try:
                store = await knowledge_svc_handle.get_facts(criteria=fact_data)
                await knowledge_svc_handle.delete_fact(criteria=fact_data)
                resp = await self._api_manager.verify_fact_integrity(store)
                return web.json_response(dict(removed=resp))
            except Exception as e:
                self.log.warning(f'Encountered issue removing fact {fact_data} - {e}')
        raise JsonHttpBadRequest('Invalid fact data was provided.')

    @aiohttp_apispec.docs(tags=['relationships'])
    @aiohttp_apispec.response_schema(RelationshipSchema)
    async def delete_relationships(self, request: web.Request):
        knowledge_svc_handle = self._api_manager.knowledge_svc
        relationship_data = await self._api_manager.extract_data(request)
        if relationship_data:
            try:
                store = await knowledge_svc_handle.get_relationships(criteria=relationship_data)
                await knowledge_svc_handle.delete_relationship(criteria=relationship_data)
                resp = await self._api_manager.verify_relationship_integrity(store)
                return web.json_response(dict(removed=resp))
            except Exception as e:
                self.log.warning(f'Encountered issue removing relationship {relationship_data} - {e}')
        raise JsonHttpBadRequest('Invalid relationship data was provided.')

    @aiohttp_apispec.docs(tags=['facts'])
    @aiohttp_apispec.request_schema(FactUpdateRequestSchema)
    @aiohttp_apispec.response_schema(FactSchema)
    async def update_facts(self, request: web.Request):
        knowledge_svc_handle = self._api_manager.knowledge_svc
        fact_data = await self._api_manager.extract_data(request)
        try:
            await knowledge_svc_handle.update_fact(criteria=fact_data['criteria'],
                                                   updates=fact_data['updates'])
            temp = await self._api_manager.copy_object(fact_data['criteria'])
            for k in fact_data['updates']:
                temp[k] = fact_data['updates'][k]
            store = await knowledge_svc_handle.get_facts(criteria=temp)
            resp = await self._api_manager.verify_fact_integrity(store)
            return web.json_response(dict(updated=resp))
        except Exception as e:
            error_msg = f'Encountered issue updating fact {fact_data} - {e}'
            self.log.warning(error_msg)
            raise JsonHttpBadRequest(error_msg)

    @aiohttp_apispec.docs(tags=['relationships'])
    @aiohttp_apispec.request_schema(RelationshipUpdateSchema)
    @aiohttp_apispec.response_schema(RelationshipSchema)
    async def update_relationships(self, request: web.Request):
        knowledge_svc_handle = self._api_manager.knowledge_svc
        relationship_data = await self._api_manager.extract_data(request)
        try:
            await knowledge_svc_handle.update_relationship(criteria=relationship_data['criteria'],
                                                           updates=relationship_data['updates'])
            temp = await self._api_manager.copy_object(relationship_data['criteria'])
            for k in relationship_data['updates']:
                if isinstance(relationship_data['updates'][k], dict):
                    handle = dict()
                    if k in relationship_data['criteria'] and \
                            isinstance(relationship_data['criteria'][k], dict):
                        handle = relationship_data['criteria'][k]
                    for j in relationship_data['updates'][k]:
                        handle[j] = relationship_data['updates'][k][j]
                    temp[k] = handle
                else:
                    temp[k] = relationship_data['updates'][k]
            store = await knowledge_svc_handle.get_relationships(criteria=temp)
            resp = await self._api_manager.verify_relationship_integrity(store)
            return web.json_response(dict(updated=resp))
        except Exception as e:
            error_msg = f'Encountered issue updating relationship {relationship_data} - {e}'
            self.log.warning(error_msg)
            raise JsonHttpBadRequest(error_msg)
