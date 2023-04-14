from app.api.v2.managers.base_api_manager import BaseApiManager
from app.objects.c_adversary import Adversary


class AdversaryApiManager(BaseApiManager):
    def __init__(self, data_svc, file_svc, planning_svc):
        super().__init__(data_svc=data_svc, file_svc=file_svc)
        self._planning_svc = planning_svc

    async def verify_adversary(self, adversary: Adversary):
        adversary.verify(log=self.log, abilities=self._data_svc.ram['abilities'],
                         objectives=self._data_svc.ram['objectives'])
        return adversary

    async def fact_analysis(self, ram_key, adversary_id: str = None, atomic_ordering: list = None):
        fa = dict(errors=[])
        if adversary_id is not None:
            adversary = self.find_object(ram_key, dict(adversary_id=adversary_id))
        elif atomic_ordering is not None:
            adversary = Adversary(name='prototype', atomic_ordering=atomic_ordering, description='Not full adversary. Only has atomic ordering field.')
        else:
            fa['errors'].append('Could not find adversary, or "atomic_ordering" field not supplied.')
            return
        return await self._planning_svc.adversary_fact_requirements(adversary)
