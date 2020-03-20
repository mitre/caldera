from base64 import b64decode
from datetime import datetime
from urllib.parse import urlparse

import marshmallow as ma

from app.utility.base_object import BaseObject


class Agent(BaseObject):

    RESERVED = dict(server='#{server}', group='#{group}', agent_paw='#{paw}', location='#{location}',
                    exe_name='#{exe_name}')

    class AgentSchema(ma.Schema):
        paw = ma.fields.String()
        group = ma.fields.String()
        architecture = ma.fields.String()
        platform = ma.fields.String()
        server = ma.fields.String()
        location = ma.fields.String()
        pid = ma.fields.Integer()
        ppid = ma.fields.Integer()
        trusted = ma.fields.Boolean()
        last_seen = ma.fields.DateTime(format='%Y-%m-%d %H:%M:%S')
        sleep_min = ma.fields.Integer()
        sleep_max = ma.fields.Integer()
        executors = ma.fields.List(ma.fields.String())
        privilege = ma.fields.String()
        display_name = ma.fields.String()
        exe_name = ma.fields.String()
        host = ma.fields.String()
        watchdog = ma.fields.Integer()
        contact = ma.fields.String()

    @property
    def unique(self):
        return self.hash(self.paw)

    @property
    def display(self):
        return self.AgentSchema().dump(self)

    @property
    def display_name(self):
        return '{}${}'.format(self.host, self.username)

    def __init__(self, sleep_min, sleep_max, watchdog, platform='unknown', server='unknown', host='unknown',
                 username='unknown', architecture='unknown', group='red', location='unknown', pid=0, ppid=0,
                 trusted=True, executors=(), privilege='User', exe_name='unknown', contact='unknown', paw=None):
        super().__init__()
        self.paw = paw if paw else self.generate_name(size=6)
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
        self.executors = executors
        self.privilege = privilege
        self.exe_name = exe_name
        self.sleep_min = int(sleep_min)
        self.sleep_max = int(sleep_max)
        self.watchdog = int(watchdog)
        self.contact = contact
        self.access = self.Access.BLUE if group == 'blue' else self.Access.RED

    @classmethod
    def from_dict(cls, dict_obj):
        """ Creates an Agent object from parameters stored in a dict. AgentSchema is used to validate inputs."""
        return cls(**cls.AgentSchema().load(dict_obj))

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
        if self.executors:
            preferred = 'psh' if 'psh' in self.executors else self.executors[0]
            executors = self.executors
            for ai in set([pa.ability_id for pa in ability_set]):
                total_ability = [ab for ab in ability_set if (ab.ability_id == ai)
                                 and (ab.platform == self.platform) and (ab.executor in executors)]
                if len(total_ability) > 0:
                    val = next((ta for ta in total_ability if ta.executor == preferred), total_ability[0])
                    if self.privileged_to_run(val):
                        abilities.append(val)
        return abilities

    async def heartbeat_modification(self, **kwargs):
        now = datetime.now()
        self.last_seen = now
        if self.trusted:
            self.last_trusted_seen = now
        self.update('pid', kwargs.get('pid'))
        self.update('ppid', kwargs.get('ppid'))
        self.update('server', kwargs.get('server'))
        self.update('exe_name', kwargs.get('exe_name'))
        self.update('location', kwargs.get('location'))
        self.update('privilege', kwargs.get('privilege'))
        self.update('host', kwargs.get('host'))
        self.update('username', kwargs.get('username'))
        self.update('architecture', kwargs.get('architecture'))
        self.update('platform', kwargs.get('platform'))
        self.update('executors', kwargs.get('executors'))

    async def gui_modification(self, **kwargs):
        loaded = self.AgentSchema(only=('group', 'trusted', 'sleep_min', 'sleep_max', 'watchdog')).load(kwargs)
        for k, v in loaded.items():
            self.update(k, v)
        # self.update('group', kwargs.get('group'))
        # self.update('trusted', kwargs.get('trusted'))
        # self.update('sleep_min', int(kwargs['sleep_min']) if 'sleep_min' in kwargs else None)
        # self.update('sleep_max', int(kwargs['sleep_max']) if 'sleep_max' in kwargs else None)
        # self.update('watchdog', int(kwargs['watchdog']) if 'watchdog' in kwargs else None)

    async def kill(self):
        self.update('watchdog', 1)
        self.update('sleep_min', 60 * 2)
        self.update('sleep_max', 60 * 2)

    def replace(self, encoded_cmd):
        decoded_cmd = b64decode(encoded_cmd).decode('utf-8', errors='ignore').replace('\n', '')
        decoded_cmd = decoded_cmd.replace(self.RESERVED['server'], self.server)
        decoded_cmd = decoded_cmd.replace(self.RESERVED['group'], self.group)
        decoded_cmd = decoded_cmd.replace(self.RESERVED['agent_paw'], self.paw)
        decoded_cmd = decoded_cmd.replace(self.RESERVED['location'], self.location)
        decoded_cmd = decoded_cmd.replace(self.RESERVED['exe_name'], self.exe_name)
        return decoded_cmd

    def privileged_to_run(self, ability):
        if not ability.privilege or self.Privileges[self.privilege].value >= self.Privileges[ability.privilege].value:
            return True
        return False
