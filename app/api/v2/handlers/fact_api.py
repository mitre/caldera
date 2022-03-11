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
        router.add_get('/facts', self.get_facts)
        router.add_get('/relationships', self.get_relationships)
        router.add_get('/facts/{operation_id}', self.get_facts_by_operation_id)
        router.add_get('/relationships/{operation_id}', self.get_relationships_by_operation_id)
        router.add_post('/facts', self.add_facts)
        router.add_post('/relationships', self.add_relationships)
        router.add_delete('/facts', self.delete_facts)
        router.add_delete('/relationships', self.delete_relationships)
        router.add_patch('/facts', self.update_facts)
        router.add_patch('/relationships', self.update_relationships)

    @aiohttp_apispec.docs(tags=['facts'],
                          summary='Retrieve Facts',
                          description='Retrieve facts by criteria. Use fields from the `FactSchema` in the request '
                                      'body to filter retrieved facts.')
    @aiohttp_apispec.querystring_schema(BaseGetAllQuerySchema)
    @aiohttp_apispec.response_schema(FactSchema(many=True, partial=True),
                                     description='Returns a list of matching facts, dumped in `FactSchema` format.')
    async def get_facts(self, request: web.Request):
        fact_data = await self._api_manager.extract_data(request)
        resp = []
        if fact_data:
            try:
                resp = await self._find_and_verify_facts(fact_data)
            except Exception as e:
                error_msg = f'Encountered issue retrieving fact {fact_data} - {e}'
                self.log.warning(error_msg)
                raise JsonHttpBadRequest(error_msg)
        return web.json_response(dict(found=resp))

    @aiohttp_apispec.docs(tags=['facts'],
                          summary='Retrieve Facts by operation id',
                          description='Retrieves facts associated with an operation. Returned facts will either be '
                                      'user-generated facts or learned facts.')
    @aiohttp_apispec.querystring_schema(BaseGetAllQuerySchema)
    @aiohttp_apispec.response_schema(FactSchema(many=True, partial=True),
                                     description='Returns a list of facts associated with operation_id, dumped in '
                                                 '`FactSchema` format.')
    async def get_facts_by_operation_id(self, request: web.Request):
        operation_id = request.match_info.get('operation_id')
        fact_data = {'source': operation_id}
        resp = []
        if fact_data:
            try:
                resp = await self._find_and_verify_facts(fact_data)
            except Exception as e:
                error_msg = f'Encountered issue retrieving facts associated with operation {operation_id} - {e}'
                self.log.warning(error_msg)
                raise JsonHttpBadRequest(error_msg)
        return web.json_response(dict(found=resp))

    @aiohttp_apispec.docs(tags=['relationships'],
                          summary="Retrieve Relationships",
                          description='Retrieve relationships by criteria. Use fields from the `RelationshipSchema` in '
                                      'the request body to filter retrieved relationships.')
    @aiohttp_apispec.response_schema(RelationshipSchema,
                                     description='Returns a list of matching relationships, dumped in '
                                     '`RelationshipSchema` format.')
    @aiohttp_apispec.querystring_schema(BaseGetAllQuerySchema)
    @aiohttp_apispec.response_schema(RelationshipSchema(many=True, partial=True))
    async def get_relationships(self, request: web.Request):
        relationship_data = await self._api_manager.extract_data(request)
        resp = []
        if relationship_data:
            try:
                resp = await self._find_and_verify_relationships(relationship_data)
            except Exception as e:
                error_msg = f'Encountered issue retrieving relationship {relationship_data} - {e}'
                self.log.warning(error_msg)
                raise JsonHttpBadRequest(error_msg)
        return web.json_response(dict(found=resp))

    @aiohttp_apispec.docs(tags=['relationships'],
                          summary="Retrieve Relationships by operation id",
                          description='Retrieve relationships associated with an operation. Returned relationships '
                                      'will be either user-generated relationships or learned relationships.')
    @aiohttp_apispec.response_schema(RelationshipSchema,
                                     description='Returns a list of matching relationships, dumped in '
                                                 '`RelationshipSchema` format.')
    @aiohttp_apispec.querystring_schema(BaseGetAllQuerySchema)
    @aiohttp_apispec.response_schema(RelationshipSchema(many=True, partial=True))
    async def get_relationships_by_operation_id(self, request: web.Request):
        operation_id = request.match_info.get('operation_id')
        relationship_data = {'origin': operation_id}
        resp = []
        if relationship_data:
            try:
                resp = await self._find_and_verify_relationships(relationship_data)
            except Exception as e:
                error_msg = f'Encountered issue retrieving relationships associated with operation' \
                            f' {operation_id} - {e}'
                self.log.warning(error_msg)
                raise JsonHttpBadRequest(error_msg)
        return web.json_response(dict(found=resp))

    @aiohttp_apispec.docs(tags=['facts'],
                          summary='Create a Fact',
                          description='Create a new fact using the format provided in the `FactSchema`.')
    @aiohttp_apispec.request_schema(FactSchema)
    @aiohttp_apispec.response_schema(FactSchema, description='Returns the created fact, dumped in `FactSchema` format.')
    async def add_facts(self, request: web.Request):
        knowledge_svc_handle = self._api_manager.knowledge_svc
        fact_data = await self._api_manager.extract_data(request)
        try:
            new_fact = Fact.load(fact_data)
            if 'source' not in fact_data:
                new_fact.source = WILDCARD_STRING
            new_fact.origin_type = OriginType.USER
            await self._api_manager.verify_operation_state(new_fact)
            await knowledge_svc_handle.add_fact(new_fact)
            store = await knowledge_svc_handle.get_facts(criteria=dict(trait=new_fact.trait,
                                                                       value=new_fact.value,
                                                                       source=new_fact.source,
                                                                       origin_type=OriginType.USER))
            resp = await self._api_manager.verify_fact_integrity(store)
            return web.json_response(dict(added=resp))
        except Exception as e:
            error_msg = f'Encountered issue saving fact {fact_data} - {e}'
            self.log.warning(error_msg)
            raise JsonHttpBadRequest(error_msg)

    @aiohttp_apispec.docs(tags=['relationships'],
                          summary='Create a Relationship',
                          description='Create a new relationship using the format provided in the '
                                      '`RelationshipSchema`.')
    @aiohttp_apispec.request_schema(RelationshipSchema)
    @aiohttp_apispec.response_schema(RelationshipSchema,
                                     description='Returns the created relationship, dumped in `RelationshipSchema` '
                                                 'format.')
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
            new_relationship.source.origin_type = OriginType.USER
            if 'target' in relationship_data:
                new_relationship.target.source = origin_target
                new_relationship.target.origin_type = OriginType.USER
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

    @aiohttp_apispec.docs(tags=['facts'],
                          summary='Delete One or More Facts',
                          description='Delete facts using the format provided in the `FactSchema`. '
                                      'This will delete all facts that match the criteria specified in the payload.')
    @aiohttp_apispec.request_schema(FactSchema(partial=True))
    @aiohttp_apispec.response_schema(FactSchema,
                                     description='Returns the deleted fact(s), dumped in `FactSchema` format.')
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

    @aiohttp_apispec.docs(tags=['relationships'],
                          summary='Delete One or More Relationships',
                          description=('Delete relationships using the format provided in the RelationshipSchema. '
                                       'This will delete all relationships that match the criteria specified in the '
                                       'payload.'))
    @aiohttp_apispec.response_schema(RelationshipSchema,
                                     description='Returns the deleted relationship(s), dumped in RelationshipSchema '
                                                 'format.')
    @aiohttp_apispec.request_schema(RelationshipSchema(partial=True))
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

    @aiohttp_apispec.docs(tags=['facts'],
                          summary='Update One or More Facts',
                          description=('Update existing facts using the format provided in the `FactSchema`. '
                                       'This will update all facts that match the criteria specified in the payload.'))
    @aiohttp_apispec.request_schema(FactUpdateRequestSchema(partial=True))
    @aiohttp_apispec.response_schema(FactSchema,
                                     description='Returns the updated fact(s), dumped in `FactSchema` format.')
    async def update_facts(self, request: web.Request):
        knowledge_svc_handle = self._api_manager.knowledge_svc
        fact_data = await self._api_manager.extract_data(request)
        if 'criteria' in fact_data and 'updates' in fact_data:
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
        raise JsonHttpBadRequest("Need a 'criteria' to match on and 'updates' to apply.")

    @aiohttp_apispec.docs(tags=['relationships'],
                          summary='Update One or More Relationships',
                          description=('Update existing relationships using the format provided in the '
                                       '`RelationshipSchema`. This will update all relationships that match the '
                                       'criteria specified in the payload.'))
    @aiohttp_apispec.request_schema(RelationshipUpdateSchema(partial=True))
    @aiohttp_apispec.response_schema(RelationshipSchema,
                                     description='Returns the updated relationship(s), dumped in `RelationshipSchema` '
                                                 'format.')
    async def update_relationships(self, request: web.Request):
        knowledge_svc_handle = self._api_manager.knowledge_svc
        relationship_data = await self._api_manager.extract_data(request)
        if 'criteria' in relationship_data and 'updates' in relationship_data:
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
        raise JsonHttpBadRequest("Need a 'criteria' to match on and 'updates' to apply.")

    async def _find_and_verify_facts(self, fact_data: dict):
        knowledge_svc_handle = self._api_manager.knowledge_svc
        FactSchema(partial=True).load(fact_data)
        store = await knowledge_svc_handle.get_facts(criteria=fact_data)
        return await self._api_manager.verify_fact_integrity(store)

    async def _find_and_verify_relationships(self, relationship_data):
        knowledge_svc_handle = self._api_manager.knowledge_svc
        RelationshipSchema(partial=True).load(relationship_data)
        store = await knowledge_svc_handle.get_relationships(criteria=relationship_data)
        return await self._api_manager.verify_relationship_integrity(store)
