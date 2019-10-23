from app.objects.base_object import BaseObject


class Agent(BaseObject):

    @property
    def unique(self):
        return self.paw

    @property
    def display(self):
        return dict(paw=self.paw, group=self.group, architecture=self.architecture, platform=self.platform,
                    server=self.server, location=self.location, pid=self.pid, ppid=self.ppid, trusted=self.trusted,
                    last_seen=self.last_seen, last_trusted_seen=self.last_trusted_seen, sleep_min=self.sleep_min,
                    sleep_max=self.sleep_max, executors=self.executors)

    def __init__(self, paw, last_seen=None, architecture=None, platform=None, server=None, group=None,
                 location=None, pid=None, ppid=None, trusted=None, last_trusted_seen=None, sleep_min=None,
                 sleep_max=None, executors=None):
        self.paw = paw
        self.group = group
        self.architecture = architecture
        self.platform = platform
        self.server = server
        self.location = location
        self.pid = pid
        self.ppid = ppid
        self.trusted = trusted
        self.last_seen = last_seen
        self.last_trusted_seen = last_trusted_seen
        self.sleep_min = sleep_min
        self.sleep_max = sleep_max
        self.executors = executors

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
        return existing

