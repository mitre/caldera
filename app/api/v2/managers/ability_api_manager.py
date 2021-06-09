# from app.api.v2 import validation
from app.api.v2.managers.base_api_manager import BaseApiManager


class AbilityUpdateNotAllowed(Exception):
    def __init__(self, property, message=None):
        super().__init__(message or f'Updating ability property is disallowed: {property}')
        self.property = property


class AbilityNotFound(Exception):
    def __init__(self, ability_id, message=None):
        super().__init__(message or f'Ability not found: {ability_id}')
        self.ability_id = ability_id


class AbilityApiManager(BaseApiManager):
    def __init__(self, data_svc, rest_svc):
        super().__init__(data_svc=data_svc)
        self._rest_svc = rest_svc

    async def create_abilities(self, access, ability_list):
        data = dict(bulk=ability_list)
        return await self._rest_svc.persist_ability(access=access, data=data)

    def update_ability(self, prop, value):
        pass

    async def delete_ability(self, ability_id):
        result = await self._rest_svc.delete_ability(ability_id)
        return result
