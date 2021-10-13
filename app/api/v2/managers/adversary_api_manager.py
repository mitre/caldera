from app.api.v2.managers.base_api_manager import BaseApiManager
from app.objects.c_adversary import Adversary


class AdversaryApiManager(BaseApiManager):
    def __init__(self, data_svc, file_svc):
        super().__init__(data_svc=data_svc, file_svc=file_svc)

    async def verify_adversary(self, adversary: Adversary):
        adversary.verify(log=self.log, abilities=self._data_svc.ram['abilities'],
                         objectives=self._data_svc.ram['objectives'])
        return adversary
