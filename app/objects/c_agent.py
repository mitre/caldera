from datetime import datetime
from urllib.parse import urlparse

from app.utility.base_object import BaseObject


class Agent(BaseObject):

    @property
    def unique(self):
        return self.hash(self.paw)

    @property
    def display(self):
        return dict(paw=self.paw, group=self.group, architecture=self.architecture, platform=self.platform,
                    server=self.server, location=self.location, pid=self.pid, ppid=self.ppid, trusted=self.trusted,
                    last_seen=self.last_seen.strftime('%Y-%m-%d %H:%M:%S'),
                    sleep_min=self.sleep_min, sleep_max=self.sleep_max, executors=self.executors,
                    privilege=self.privilege, display_name=self.display_name, exe_name=self.exe_name, host=self.host,
                    watchdog=self.watchdog)

    @property
    def display_name(self):
        return '{}${}'.format(self.host, self.username)

    def __init__(self, paw, platform=None, server=None, host='unknown', username='unknown', architecture='unknown',
                 group='default', location='unknown', pid=0, ppid=0, trusted=True, executors=(), privilege='User',
                 c2='HTTP', exe_name='unknown'):
        super().__init__()
        self.paw = paw
        self.host = host
        self.username = username
        self.group = group
        self.architecture = architecture
        self.platform = platform
        url = urlparse(server)
        self.server = '%s://%s:%s' % (url.scheme, url.hostname, url.port)
        self.location = location
        self.pid = pid
        self.ppid = ppid
        self.trusted = trusted
        self.created = datetime.now()
        self.last_seen = self.created
        self.last_trusted_seen = self.created
        self.sleep_min = 55
        self.sleep_max = 65
        self.executors = executors
        self.privilege = privilege
        self.c2 = c2
        self.exe_name = exe_name
        self.watchdog = 0

    def store(self, ram):
        existing = self.retrieve(ram['agents'], self.unique)
        if not existing:
            ram['agents'].append(self)
            return self.retrieve(ram['agents'], self.unique)
        return existing

    async def calculate_sleep(self):
        return self.jitter('%d/%d' % (self.sleep_min, self.sleep_max))

    async def capabilities(self, ability_set):
        abilities = []
        preferred = self.executors[0]
        executors = self.executors
        for ai in set([pa.ability_id for pa in ability_set]):
            total_ability = [ab for ab in ability_set if (ab.ability_id == ai)
                             and (ab.platform == self.platform) and (ab.executor in executors)]
            if len(total_ability) > 0:
                val = next((ta for ta in total_ability if ta.executor == preferred), total_ability[0])
                if val.privilege and val.privilege == self.privilege or not val.privilege:
                    abilities.append(val)
        return abilities

    async def update(self):
        now = datetime.now()
        self.last_seen = now
        if self.trusted:
            self.last_trusted_seen = now

