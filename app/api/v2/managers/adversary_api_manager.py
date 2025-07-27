from app.api.v2.managers.base_api_manager import BaseApiManager
from app.objects.c_adversary import Adversary
import traceback


class AdversaryApiManager(BaseApiManager):
    def __init__(self, data_svc, file_svc):
        super().__init__(data_svc=data_svc, file_svc=file_svc)

    async def verify_adversary(self, adversary: Adversary):
        if not adversary:
            self.log.warning('call stack verify_adversary: %s',''.join(traceback.format_stack()))
        try:
            adversary.verify(
                log=self.log,
                abilities=self._data_svc.ram['abilities'],
                objectives=self._data_svc.ram['objectives']
            )
            self.log.debug('[verify_adversary] Successfully verified adversary: %s', adversary.display)
            return adversary
        except Exception as e:
            self.log.exception('[verify_adversary] Exception during verify: %s', str(e))
            raise

