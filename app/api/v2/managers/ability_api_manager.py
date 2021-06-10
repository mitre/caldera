from app.api.v2.managers.base_api_manager import BaseApiManager
from app.objects.c_ability import Ability


class AbilityApiManager(BaseApiManager):
    def __init__(self, data_svc, file_svc):
        super().__init__(data_svc=data_svc)
        self._file_svc = file_svc

    async def verify_ability(self, ability: Ability):
        ability.verify(log=self.log)
        return ability
