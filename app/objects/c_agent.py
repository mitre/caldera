import re
from base64 import b64decode
from datetime import datetime, timezone
from urllib.parse import urlparse

import marshmallow as ma

from app.objects.interfaces.i_object import FirstClassObjectInterface
from app.objects.secondclass.c_link import Link, LinkSchema
from app.objects.secondclass.c_fact import OriginType
from app.utility.base_object import BaseObject
from app.utility.base_planning_svc import BasePlanningService
from app.utility.base_service import BaseService


class AgentFieldsSchema(ma.Schema):

    paw = ma.fields.String(allow_none=True)
    sleep_min = ma.fields.Integer()
    sleep_max = ma.fields.Integer()
    watchdog = ma.fields.Integer()
    group = ma.fields.String()
    architecture = ma.fields.String()
    platform = ma.fields.String()
    server = ma.fields.String()
    upstream_dest = ma.fields.String(allow_none=True)
    username = ma.fields.String()
    location = ma.fields.String()
    pid = ma.fields.Integer()
    ppid = ma.fields.Integer()
    trusted = ma.fields.Boolean()
    executors = ma.fields.List(ma.fields.String())
    privilege = ma.fields.String()
    exe_name = ma.fields.String()
    host = ma.fields.String()
    contact = ma.fields.String()
    proxy_receivers = ma.fields.Dict(keys=ma.fields.String(), values=ma.fields.List(ma.fields.String()),
                                     allow_none=True)
    proxy_chain = ma.fields.List(ma.fields.List(ma.fields.String()), allow_none=True)
    origin_link_id = ma.fields.String()
    deadman_enabled = ma.fields.Boolean(allow_none=True)
    available_contacts = ma.fields.List(ma.fields.String(), allow_none=True)
    host_ip_addrs = ma.fields.List(ma.fields.String(), allow_none=True)

    display_name = ma.fields.String(dump_only=True)
    created = ma.fields.DateTime(format=BaseObject.TIME_FORMAT, dump_only=True)
    last_seen = ma.fields.DateTime(format=BaseObject.TIME_FORMAT, dump_only=True)
    links = ma.fields.List(ma.fields.Nested(LinkSchema), dump_only=True)
    pending_contact = ma.fields.String()

    @ma.pre_load
    def remove_nulls(self, in_data, **_):
        return {k: v for k, v in in_data.items() if v is not None}

    @ma.pre_load
    def remove_properties(self, data, **_):
        data.pop('display_name', None)
        data.pop('created', None)
        data.pop('last_seen', None)
        data.pop('links', None)
        return data


class AgentSchema(AgentFieldsSchema):

    @ma.post_load
    def build_agent(self, data, **kwargs):
        return None if kwargs.get('partial') is True else Agent(**data)


class Agent(FirstClassObjectInterface, BaseObject):

    schema = AgentSchema()
    load_schema = AgentSchema(partial=['paw', 'origin_link_id'])

    RESERVED = dict(server='#{server}', group='#{group}', agent_paw='#{paw}', location='#{location}',
                    exe_name='#{exe_name}', upstream_dest='#{upstream_dest}',
                    payload=re.compile('#{payload:(.*?)}', flags=re.DOTALL))

    @property
    def unique(self):
        return self.hash(self.paw)

    @property
    def display_name(self):
        return '{}${}'.format(self.host, self.username)

    @classmethod
    def is_global_variable(cls, variable):
        if variable.startswith('payload:'):
            return True
        if variable == 'payload':
            return False
        if variable in cls.RESERVED:
            return True
        return False

    def __init__(self, sleep_min=30, sleep_max=60, watchdog=0, platform='unknown', server='unknown', host='unknown',
                 username='unknown', architecture='unknown', group='red', location='unknown', pid=0, ppid=0,
                 trusted=True, executors=(), privilege='User', exe_name='unknown', contact='unknown', paw=None,
                 proxy_receivers=None, proxy_chain=None, origin_link_id='', deadman_enabled=False,
                 available_contacts=None, host_ip_addrs=None, upstream_dest=None, pending_contact=None):
        super().__init__()
        self.paw = paw if paw else self.generate_name(size=6)
        self.host = host
        self.username = username
        self.group = group
        self.architecture = architecture
        self.platform = platform.lower()
        url = urlparse(server)
        self.server = '%s://%s:%s' % (url.scheme, url.hostname, url.port)
        self.location = location
        self.pid = pid
        self.ppid = ppid
        self.trusted = trusted
        self.created = datetime.now(timezone.utc)
        self.last_seen = self.created
        self.last_trusted_seen = self.created
        self.executors = executors
        self.privilege = privilege
        self.exe_name = exe_name
        self.sleep_min = int(sleep_min)
        self.sleep_max = int(sleep_max)
        self.watchdog = int(watchdog)
        self.contact = contact
        self.links = []
        self.access = self.Access.BLUE if group == 'blue' else self.Access.RED
        self.proxy_receivers = proxy_receivers if proxy_receivers else dict()
        self.proxy_chain = proxy_chain if proxy_chain else []
        self.origin_link_id = origin_link_id
        self.deadman_enabled = deadman_enabled
        self.available_contacts = available_contacts if available_contacts else [self.contact]
        self.pending_contact = pending_contact if pending_contact else contact
        self.host_ip_addrs = host_ip_addrs if host_ip_addrs else []
        if upstream_dest:
            upstream_url = urlparse(upstream_dest)
            self.upstream_dest = '%s://%s:%s' % (upstream_url.scheme, upstream_url.hostname, upstream_url.port)
        else:
            self.upstream_dest = self.server
        self._executor_change_to_assign = None
        self.log = self.create_logger('agent')

    def store(self, ram):
        existing = self.retrieve(ram['agents'], self.unique)
        if not existing:
            ram['agents'].append(self)
            return self.retrieve(ram['agents'], self.unique)
        existing.update('group', self.group)
        existing.update('trusted', self.trusted)
        existing.update('sleep_min', self.sleep_min)
        existing.update('sleep_max', self.sleep_max)
        existing.update('watchdog', self.watchdog)
        existing.update('pending_contact', self.pending_contact)
        return existing

    async def calculate_sleep(self):
        return self.jitter('%d/%d' % (self.sleep_min, self.sleep_max))

    async def capabilities(self, abilities):
        """Get abilities that the agent is capable of running
        :param abilities: List of abilities to check agent capability
        :type abilities: List[Ability]
        :return: List of abilities the agents is capable of running
        :rtype: List[Ability]
        """
        capabilities = []
        for ability in abilities:
            if self.privileged_to_run(ability) and ability.find_executors(self.executors, self.platform):
                capabilities.append(ability)
        return capabilities

    async def get_preferred_executor(self, ability):
        """Get preferred executor for ability
        Will return None if the agent is not capable of running any
        executors in the given ability.
        :param ability: Ability to get preferred executor for
        :type ability: Ability
        :return: Preferred executor or None
        :rtype: Union[Executor, None]
        """
        potential_executors = ability.find_executors(self.executors, self.platform)
        if not potential_executors:
            return None

        preferred_executor_name = self._get_preferred_executor_name()
        for executor in potential_executors:
            if executor.name == preferred_executor_name:
                return executor
        return potential_executors[0]

    async def heartbeat_modification(self, **kwargs):
        now = datetime.now(timezone.utc)
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
        self.update('proxy_receivers', kwargs.get('proxy_receivers'))
        self.update('proxy_chain', kwargs.get('proxy_chain'))
        self.update('deadman_enabled', kwargs.get('deadman_enabled'))
        self.update('contact', kwargs.get('contact'))
        self.update('host_ip_addrs', kwargs.get('host_ip_addrs'))
        self.update('upstream_dest', kwargs.get('upstream_dest'))
        if not self._executor_change_to_assign:
            # Don't update executors if we're waiting to assign an executor change to the agent.
            self.update('executors', kwargs.get('executors'))

    async def gui_modification(self, **kwargs):
        loaded = AgentFieldsSchema(only=('group', 'trusted', 'sleep_min', 'sleep_max', 'watchdog', 'pending_contact')).load(kwargs)
        for k, v in loaded.items():
            self.update(k, v)

    async def kill(self):
        self.update('watchdog', 1)
        self.update('sleep_min', 60 * 2)
        self.update('sleep_max', 60 * 2)

    def replace(self, encoded_cmd, file_svc):
        decoded_cmd = b64decode(encoded_cmd).decode('utf-8', errors='ignore').replace('\n', '')
        decoded_cmd = decoded_cmd.replace(self.RESERVED['server'], self.server)
        decoded_cmd = decoded_cmd.replace(self.RESERVED['group'], self.group)
        decoded_cmd = decoded_cmd.replace(self.RESERVED['agent_paw'], self.paw)
        decoded_cmd = decoded_cmd.replace(self.RESERVED['location'], self.location)
        decoded_cmd = decoded_cmd.replace(self.RESERVED['exe_name'], self.exe_name)
        decoded_cmd = decoded_cmd.replace(self.RESERVED['upstream_dest'], self.upstream_dest)
        decoded_cmd = self._replace_payload_data(decoded_cmd, file_svc)
        return decoded_cmd

    def privileged_to_run(self, ability):
        if not ability.privilege or self.Privileges[self.privilege].value >= self.Privileges[ability.privilege].value:
            return True
        return False

    async def bootstrap(self, data_svc):
        abilities = []
        for i in self.get_config(name='agents', prop='bootstrap_abilities'):
            for a in await data_svc.locate('abilities', match=dict(ability_id=i)):
                abilities.append(a)
        await self.task(abilities, obfuscator='plain-text')

    async def deadman(self, data_svc):
        abilities = []
        deadman_abilities = self.get_config(name='agents', prop='deadman_abilities')
        if deadman_abilities:
            for i in deadman_abilities:
                for a in await data_svc.locate('abilities', match=dict(ability_id=i)):
                    abilities.append(a)
        await self.task(abilities, obfuscator='plain-text', deadman=True)

    async def task(self, abilities, obfuscator, facts=(), deadman=False):
        if not self.executors:
            return []

        bps = BasePlanningService()
        preferred_executor_name = self._get_preferred_executor_name()

        links = []
        for ability in await self.capabilities(abilities):
            executors = ability.find_executors(self.executors, self.platform)
            executors = sorted(executors, key=lambda ex: ex.name == preferred_executor_name, reverse=True)

            for executor in executors:
                ex_links = [Link.load(dict(command=self.encode_string(executor.test), paw=self.paw, ability=ability,
                                           executor=executor, deadman=deadman))]
                valid_links = await bps.add_test_variants(links=ex_links, agent=self, facts=facts, trim_unset_variables=True)
                if valid_links:
                    links.extend(valid_links)
                    break

        links = await bps.obfuscate_commands(self, obfuscator, links)
        knowledge_svc_handle = BaseService.get_service('knowledge_svc')
        for fact in facts:
            fact.source = self.paw
            fact.origin_type = OriginType.SEEDED
            await knowledge_svc_handle.add_fact(fact)
        self.links.extend(links)
        return links

    async def all_facts(self):
        knowledge_svc_handle = BaseService.get_service('knowledge_svc')
        return await knowledge_svc_handle.get_facts(dict(source=self.paw))

    @property
    def executor_change_to_assign(self):
        return self._executor_change_to_assign

    def set_pending_executor_removal(self, executor_name):
        """Mark specified executor to remove.
        :param executor_name: name of executor for agent to remove
        :type executor_name: str
        """
        if executor_name and isinstance(executor_name, str):
            if executor_name in self.executors:
                # Remove the executor server-side so planners can generate appropriate links immediately.
                self.executors.remove(executor_name)
                self._executor_change_to_assign = dict(action='remove', executor=executor_name)
        else:
            self.log.error('Paw %s: Invalid executor name. Please provide non-empty string. Provided value: %s',
                           self.paw, executor_name)

    def set_pending_executor_path_update(self, executor_name, new_binary_path):
        """Mark specified executor to update its binary path to the new path.
        :param executor_name: name of executor for agent to update binary path
        :type executor_name: str
        :param new_binary_path: new binary path for executor to reference
        :type new_binary_path: str
        """
        if executor_name and new_binary_path and isinstance(executor_name, str) and isinstance(new_binary_path, str):
            if executor_name in self.executors:
                self._executor_change_to_assign = dict(action='update_path', executor=executor_name,
                                                       value=new_binary_path)
        else:
            self.log.error('Paw %s: Invalid format for executor name or new binary path. '
                           'Please provide non-empty strings. Provided values: %s, %s',
                           self.paw, executor_name, new_binary_path)

    def assign_pending_executor_change(self):
        """Return the executor change dict and remove pending change to assign.
        :return: Dict representing the executor change that is assigned.
        :rtype: dict(str, str)
        """
        executor_change = self.executor_change_to_assign
        self._executor_change_to_assign = None
        return executor_change

    def _replace_payload_data(self, decoded_cmd, file_svc):
        for uuid in re.findall(self.RESERVED['payload'], decoded_cmd):
            if self.is_uuid4(uuid):
                _, display_name = file_svc.get_payload_name_from_uuid(uuid)
                decoded_cmd = decoded_cmd.replace('#{payload:%s}' % uuid, display_name)
        return decoded_cmd

    def _get_preferred_executor_name(self):
        if 'psh' in self.executors:
            return 'psh'
        elif 'sh' in self.executors:
            return 'sh'
        return self.executors[0]
