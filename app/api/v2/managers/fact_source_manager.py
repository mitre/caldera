from app.api.v2.managers.base_api_manager import BaseApiManager


class FactSourceApiManager(BaseApiManager):
    def __init__(self, data_svc, file_svc, knowledge_svc):
        super().__init__(data_svc=data_svc, file_svc=file_svc)
        self.knowledge_svc = knowledge_svc
