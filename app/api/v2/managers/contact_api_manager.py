from app.api.v2.managers.base_api_manager import BaseApiManager
from app.api.v2.responses import JsonHttpNotFound


class ContactApiManager(BaseApiManager):
    def __init__(self, data_svc, file_svc, contact_svc):
        super().__init__(data_svc=data_svc, file_svc=file_svc)
        self.contact_svc = contact_svc

    def get_contact_report(self, contact: str = None):
        contact = contact.upper()
        if contact in self.contact_svc.report:
            return self.contact_svc.report.get(contact)
        raise JsonHttpNotFound(f'Contact not found: {contact}')

    def get_available_contact_reports(self):
        return list(self.contact_svc.report.keys())
