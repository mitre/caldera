import re
from base64 import b64decode
from datetime import datetime
from urllib.parse import urlparse

import marshmallow as ma

from app.objects.interfaces.i_object import FirstClassObjectInterface
from app.objects.secondclass.c_link import Link, LinkSchema
from app.utility.base_object import BaseObject
from app.utility.base_planning_svc import BasePlanningService


class AgentFieldsSchema(ma.Schema):

    paw = ma.fields.String()
    group = ma.fields.String()
    architecture = ma.fields.String()
    platform = ma.fields.String()
    server = ma.fields.String()
    upstream_dest = ma.fields.String()
    username = ma.fields.String()
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
    pending_contact = ma.fields.String()
    links = ma.fields.List(ma.fields.Nested(LinkSchema()))
    proxy_receivers = ma.fields.Dict(keys=ma.fields.String(), values=ma.fields.List(ma.fields.String()))
    proxy_chain = ma.fields.List(ma.fields.List(ma.fields.String()))
    origin_link_id = ma.fields.Integer()
    deadman_enabled = ma.fields.Boolean()
    available_contacts = ma.fields.List(ma.fields.String())
    created = ma.fields.DateTime(format='%Y-%m-%d %H:%M:%S')
    host_ip_addrs = ma.fields.List(ma.fields.String())

    @ma.pre_load
    def remove_nulls(self, in_data, **_):
        return {k: v for k, v in in_data.items() if v is not None}


class AgentSchema(AgentFieldsSchema):

    @ma.post_load
    def build_agent(self, data, **_):
        return Agent(**data)


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

    def __init__(self, sleep_min, sleep_max, watchdog, platform='unknown', server='unknown', host='unknown',
                 username='unknown', architecture='unknown', group='red', location='unknown', pid=0, ppid=0,
                 trusted=True, executors=(), privilege='User', exe_name='unknown', contact='unknown', paw=None,
                 proxy_receivers=None, proxy_chain=None, origin_link_id=0, deadman_enabled=False,
                 available_contacts=None, host_ip_addrs=None, upstream_dest=None):
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
        self.links = []
        self.access = self.Access.BLUE if group == 'blue' else self.Access.RED
        self.proxy_receivers = proxy_receivers if proxy_receivers else dict()
        self.proxy_chain = proxy_chain if proxy_chain else []
        self.origin_link_id = origin_link_id
        self.deadman_enabled = deadman_enabled
        self.available_contacts = available_contacts if available_contacts else [self.contact]
        self.pending_contact = contact
        self.host_ip_addrs = host_ip_addrs if host_ip_addrs else []
        if upstream_dest:
            upstream_url = urlparse(upstream_dest)
            self.upstream_dest = '%s://%s:%s' % (upstream_url.scheme, upstream_url.hostname, upstream_url.port)
        else:
            self.upstream_dest = self.server

    def store(self, ram):
        existing = self.retrieve(ram['agents'], self.unique)
        if not existing:
            ram['agents'].append(self)
            return self.retrieve(ram['agents'], self.unique)
        return existing

    async def calculate_sleep(self):
        return self.jitter('%d/%d' % (self.sleep_min, self.sleep_max))

    async def capabilities(self, ability_set):
        """Get abilities that the agent is capable of running

        :param ability_set: List of abilities to check agent capability
        :type ability_set: List[Ability]
        :return: List of abilities the agents is capable of running
        :rtype: List[Ability]
        """
        abilities = []
        for ability in ability_set:
            if self.privileged_to_run(ability) and ability.find_executors(self.platform, self.executors):
                abilities.append(ability)
        return abilities

    async def capabilities_with_preferred_executor(self, ability_set):
        """Get abilities that the agent is capable of running along with preferred executor

        :param ability_set: List of abilities to check agent capability
        :type ability_set: List[Ability]
        :return: List of abilities with preferred executor
        :rtype: List[(Ability, Executor)]
        """
        if not self.executors:
            return []

        ability_executors = []

        for ability in ability_set:
            if not self.privileged_to_run(ability):
                continue
            executor = await self.get_preferred_executor(ability)
            if executor:
                ability_executors.append((ability, executor))
        return ability_executors

    async def get_preferred_executor(self, ability):
        """Get preferred executor for ability

        Will return None if the agent is not capable of running any
        executors in the given ability.

        :param ability: Ability to get preferred executor for
        :type ability: Ability
        :return: Preferred executor or None
        :rtype: Union[Executor, None]
        """
        preferred_executor_name = self._get_preferred_executor_name()
        potential_executors = ability.find_executors(self.platform, self.executors)
        if potential_executors:
            for executor in potential_executors:
                if executor.name == preferred_executor_name:
                    return executor
            return potential_executors[0]
        return None

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
        self.update('proxy_receivers', kwargs.get('proxy_receivers'))
        self.update('proxy_chain', kwargs.get('proxy_chain'))
        self.update('deadman_enabled', kwargs.get('deadman_enabled'))
        self.update('contact', kwargs.get('contact'))
        self.update('host_ip_addrs', kwargs.get('host_ip_addrs'))
        self.update('upstream_dest', kwargs.get('upstream_dest'))

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
            executors = ability.find_executors(self.platform, self.executors)
            executors = sorted(executors, key=lambda ex: ex.name == preferred_executor_name, reverse=True)

            for executor in executors:
                ex_links = [Link.load(dict(command=self.encode_string(executor.test), paw=self.paw, ability=ability,
                                           executor=executor, deadman=deadman))]
                variants = await bps.add_test_variants(links=ex_links, agent=self, facts=facts)
                valid_links = await bps.remove_links_missing_facts(variants)
                if valid_links:
                    for valid_link in valid_links:
                        links.append(valid_link)
                    break

        links = await bps.obfuscate_commands(self, obfuscator, links)
        self.links.extend(links)
        return links

    def all_facts(self):
        return [f for lnk in self.links for f in lnk.facts if f.score > 0]

    """ PRIVATE """

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
