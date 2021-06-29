from app.api.v2.managers.base_api_manager import BaseApiManager
from app.objects.c_adversary import Adversary


class FactApiManager(BaseApiManager):
    def __init__(self, data_svc, file_svc, knowledge_svc):
        super().__init__(data_svc=data_svc, file_svc=file_svc)
        self._knowledge_svc = knowledge_svc

    async def verify_adversary(self, adversary: Adversary):
        adversary.verify(log=self.log, abilities=self._data_svc.ram['abilities'],
                         objectives=self._data_svc.ram['objectives'])
        return adversary