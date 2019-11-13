from datetime import datetime

from app.utility.base_object import BaseObject


class Agent(BaseObject):

    @property
    def unique(self):
        return self.hash(self.paw)

    @property
    def display(self):
        return dict(paw=self.paw, group=self.group, architecture=self.architecture, platform=self.platform,
                    server=self.server, location=self.location, pid=self.pid, ppid=self.ppid, trusted=self.trusted,
                    last_seen=self.last_seen.strftime('%Y-%m-%d %H:%M:%S'), last_trusted_seen=self.last_trusted_seen,
                    sleep_min=self.sleep_min, sleep_max=self.sleep_max, executors=self.executors,
                    privilege=self.privilege, display_name=self.display_name)

    @property
    def display_name(self):
        return '{}${}'.format(self.host, self.username)

    def __init__(self, paw, host=None, username=None, architecture=None, platform=None, server=None, group=None,
                 location=None, pid=None, ppid=None, trusted=None, last_trusted_seen=None, sleep_min=None,
                 sleep_max=None, executors=None, privilege=None):
        self.paw = paw
        self.host = host
        self.username = username
        self.group = group
        self.architecture = architecture
        self.platform = platform
        self.server = server
        self.location = location
        self.pid = pid
        self.ppid = ppid
        self.trusted = trusted
        self.last_seen = datetime.now()
        self.last_trusted_seen = last_trusted_seen
        self.sleep_min = sleep_min
        self.sleep_max = sleep_max
        self.executors = executors
        self.privilege = privilege

    def store(self, ram):
        existing = self.retrieve(ram['agents'], self.unique)
        if not existing:
            ram['agents'].append(self)
            return self.retrieve(ram['agents'], self.unique)
        else:
            existing.update('trusted', self.trusted)
            if existing.trusted:
                self.update('trusted', self.last_trusted_seen)
            existing.update('last_seen', self.last_seen)
            existing.update('pid', self.pid)
            existing.update('ppid', self.ppid)
            existing.update('executors', self.executors)
            existing.update('sleep_min', self.sleep_min)
            existing.update('sleep_max', self.sleep_max)
            existing.update('group', self.group)
            existing.update('privilege', self.privilege)
        return existing

    async def calculate_sleep(self):
        return self.jitter('{}/{}'.format(self.sleep_min, self.sleep_max))

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
