from app.api.v2.managers.base_api_manager import BaseApiManager


class ContactApiManager(BaseApiManager):
    def __init__(self, data_svc, file_svc, contact_svc):
        super().__init__(data_svc=data_svc, file_svc=file_svc)
        self.contact_svc = contact_svc

    def get_contact_report(self, contact: str = None):
        if contact == 'http':
            contact = contact.upper()
        report = self.contact_svc.report.get(contact, dict())
        return report
