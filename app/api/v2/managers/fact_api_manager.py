from app.api.v2.managers.base_api_manager import BaseApiManager
from json import JSONDecodeError
from app.api.v2.responses import JsonHttpBadRequest
from aiohttp import web

class FactApiManager(BaseApiManager):
    def __init__(self, data_svc, file_svc, knowledge_svc):
        super().__init__(data_svc=data_svc, file_svc=file_svc)
        self._knowledge_svc = knowledge_svc

    @staticmethod
    async def extract_data(request: web.Request):
        fact_data = None
        if request.body_exists:
            try:
                fact_data = await request.json()
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
