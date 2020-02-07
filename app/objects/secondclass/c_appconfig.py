from app.objects.secondclass.c_fact import Fact
from app.utility.base_object import BaseObject


class AppConfig(BaseObject):

    def __init__(self, port, plugins, users, api_key, exfil_dir, reports_dir, crypt_salt, facts):
        super().__init__()
        self.port = port
        self.plugins = plugins
        self.users = users
        self.api_key = api_key
        self.exfil_dir = exfil_dir
        self.reports_dir = reports_dir
        self.crypt_salt = crypt_salt
        self.facts = [Fact(trait=f['trait'], value=f['value']) for f in facts]
