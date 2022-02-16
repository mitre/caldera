from app.api.v2.managers.base_api_manager import BaseApiManager
from app.objects.c_operation import InvalidOperationStateError
from json import JSONDecodeError
from app.api.v2.responses import JsonHttpBadRequest
from aiohttp import web

import copy
import json


class FactApiManager(BaseApiManager):
    def __init__(self, data_svc, file_svc, knowledge_svc):
        super().__init__(data_svc=data_svc, file_svc=file_svc)
        self.knowledge_svc = knowledge_svc

    @staticmethod
    async def extract_data(request: web.Request):
        fact_data = None
        raw_body = await request.read()
        if raw_body:
            try:
                fact_data = json.loads(raw_body)
            except JSONDecodeError as e:
                raise JsonHttpBadRequest('Received invalid json', details=e)
        return fact_data

    async def verify_fact_integrity(self, data):
        out = []
        for x in data:
            try:
                out.append(x.display)
            except Exception as e:
                self.log.warning(f"Unable to properly display fact {x}. Specific error encountered - {e}.")
        return out

    async def verify_relationship_integrity(self, data):
        out = []
        for x in data:
            try:
                out.append(x.flat_display)
            except Exception as e:
                self.log.warning(f"Unable to properly display relationship {x}. Specific error encountered - {e}.")
        return out

    async def verify_operation_state(self, new_fact):
        if self._data_svc.is_uuid4(new_fact.source):
            operation = (await self._data_svc.locate('operations', match=dict(id=new_fact.source)))
            if operation and await operation[0].is_finished():
                raise InvalidOperationStateError("Cannot add fact to finished operation.")

    @staticmethod
    async def copy_object(obj):
        return copy.deepcopy(obj)
