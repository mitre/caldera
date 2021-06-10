import uuid

from app.api.v2.managers.base_api_manager import BaseApiManager
from app.objects.c_adversary import Adversary


class AdversaryApiManager(BaseApiManager):
    def __init__(self, data_svc, file_svc):
        super().__init__(data_svc=data_svc, file_svc=file_svc)

    async def create_adversary(self, data: dict, access: dict):
        data['adversary_id'] = data.get('adversary_id') or str(uuid.uuid4())

        file_path = await self._get_new_object_file_path('adversaries', data['adversary_id'])
        allowed = self._get_allowed_from_access(access)

        await self._save_and_reload_object(file_path, data, Adversary, allowed)
        return await self._find_and_verify_adversary(data['adversary_id'])

    async def update_adversary(self, data: dict, search: dict):
        adversary = next(self.find_objects('adversaries', search), None)
        if not adversary:
            return None

        file_path = await self._get_existing_object_file_path(adversary.adversary_id)
        allowed = adversary.access

        existing_adversary_data = dict(self.strip_yml(file_path)[0])
        existing_adversary_data.update(data)

        await self._save_and_reload_object(file_path, existing_adversary_data, Adversary, allowed)
        return await self._find_and_verify_adversary(data['adversary_id'])

    async def replace_adversary(self, adversary: Adversary, data: dict):
        file_path = await self._get_existing_object_file_path(adversary.adversary_id)
        allowed = adversary.access

        await self._save_and_reload_object(file_path, data, Adversary, allowed)
        return await self._find_and_verify_adversary(data['adversary_id'])

    async def _find_and_verify_adversary(self, adversary_id: str):
        adversary = next(self.find_objects('adversaries', dict(adversary_id=adversary_id)))
        adversary.verify(log=self.log, abilities=self._data_svc.ram['abilities'],
                         objectives=self._data_svc.ram['objectives'])
        return adversary
