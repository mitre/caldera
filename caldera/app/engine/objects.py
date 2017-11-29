import logging
import asyncio
from .database import ExtrovirtsDocument
import mongoengine
from mongoengine import StringField, ReferenceField, DateTimeField, ListField, EmbeddedDocument, \
    BooleanField, IntField, BinaryField, DictField, EmbeddedDocumentListField, DynamicField, URLField
from ..util import tz_utcnow, CaseException

log = logging.getLogger(__name__)


class Artifactlist(ExtrovirtsDocument):
    name = StringField(required=True)
    description = StringField(required=True)
    executables = ListField(StringField())
    dlls = ListField(StringField())
    services = ListField(StringField())
    schtasks = ListField(StringField())
    file_paths = ListField(StringField())


class Domain(ExtrovirtsDocument):
    windows_domain = StringField()
    dns_domain = StringField()


class Host(ExtrovirtsDocument):
    fqdn = StringField()
    last_seen = DateTimeField()
    IP = StringField()
    domain = ReferenceField(Domain)
    hostname = StringField()
    status = StringField()


class Network(ExtrovirtsDocument):
    domain = ReferenceField(Domain)
    name = StringField()
    hosts = ListField(ReferenceField(Host))


class Agent(ExtrovirtsDocument):
    host = ReferenceField(Host)
    alive = BooleanField()
    check_in = DateTimeField()


class Opcodes(object):
    EXECUTE = "execute"
    WRITE_FILE = "write_file"
    READ_FILE = "read_file"
    EXFIL_CONNECTION = "exfil_connection"
    OPEN_SHELL = "open_shell"
    DLL_FUNCTION = "call_dll"
    REFLECTIVE_DLL_FUNCTION = "call_reflective_dll"

    arguments = {
        EXECUTE: ("command_line", "stdin"),
        WRITE_FILE: ("file_path", "contents"),
        READ_FILE: ("file_path", ),
        EXFIL_CONNECTION: ("address", "port", "file_path", "method"),
        OPEN_SHELL: tuple(),
        DLL_FUNCTION: ("file_path", "dll_function", "input"),
        REFLECTIVE_DLL_FUNCTION: ("binary", "dll_function", "input")
    }

    ALL = list(sorted(arguments.keys()))


class Rat(ExtrovirtsDocument):
    elevated = BooleanField()
    name = IntField()
    host = ReferenceField(Host)
    agent = ReferenceField(Agent)
    executable = StringField()
    username = StringField()
    active = BooleanField()


class JobException(Exception):
    pass


class HostCommand(object):
    def __init__(self):
        self.command_line = ''
        self.output = ''
        self.status = ''
        self.host = None


class CredentialEmbedded(object):
    def __init__(self):
        self.domain = ''
        self.password = ''
        self.username = ''
        self.host = None


class RatCommand(object):
    def __init__(self):
        self.host = None
        self.status = ""
        self.function = ""
        self.parameters = {}
        self.outputs = {}
        self.agent = None


class SiteUser(ExtrovirtsDocument):
    groups = ListField(StringField())
    password = BinaryField()
    username = StringField(unique=True)
    salt = BinaryField()
    email = StringField()
    last_login = DateTimeField()


class Job(ExtrovirtsDocument):
    network = ReferenceField(Network)
    agent = ReferenceField(Agent)
    action = DictField()
    create_time = DateTimeField(default=tz_utcnow)
    status = StringField(default='created')
    parser = StringField()

    @staticmethod
    def create_rat_command(rat: Rat, command: str, **params) -> 'Job':
        # Dispatch a job for Agents, to alert it of the creation of this resource
        return Job(action={
                    'rats': {
                        'hostname': rat.host.hostname,
                        'name': rat.name,
                        'function': command,
                        'parameters': params}},
                   agent=rat.agent).save()

    @staticmethod
    def create_agent_command(host: Host, command: str, **kwargs) -> 'Job':
        agent = Agent.objects(host=host)[0]
        return Job(action={command: kwargs}, agent=agent).save()

    async def wait_till_completed(self):
        waiter_task = asyncio.get_event_loop().create_task(self.wait({'status': ('success', 'failed')}))

        # give control back to the event loop so the waiter gets scheduled
        await asyncio.sleep(0)
        self.reload()

        if self.status in ('success', 'failed'):
            waiter_task.cancel()
        else:
            await waiter_task

        if self.status == 'failed':
            if self['action']['error'] == "no client":
                raise JobException("NoRatError", "Job failed because the rat was killed", self)
            elif self['action']['error'] == "agents exception":
                raise JobException("AgentExceptionError", self['action']['exception'], self)
            else:
                raise CaseException

    def host_command_result(self):
        hc = HostCommand()
        hc.status = self.status
        hc.host = self.agent.host

        try:
            hc.command_line = self.action['execute']['command_line']
        except (AttributeError, KeyError):
            pass

        if self.status == 'success':
            hc.output = self.action['result']
        return hc

    def rat_result(self):
        ivc = RatCommand()
        ivc.agent = self.agent
        ivc.host = self.agent.host
        ivc.parameters = self.action['rats']['parameters']
        if 'rats' in self.action:
            self.update_rats(ivc)
        else:
            raise Exception('Getting rat result on non-rat job')
        return ivc

    def update_rats(self, ivc):
        ivc.status = self.status
        if self.status == 'success':
            ivc.outputs = self.action['result']
        elif self.status in ("pending", "created", "failed"):
            pass
        else:
            raise CaseException()


class ObservedDomain(ExtrovirtsDocument):
    windows_domain = StringField()
    dns_domain = StringField()
    distinct_fields = [("windows_domain",), ("dns_domain",)]


class ObservedOSVersion(ExtrovirtsDocument):
    os_name = StringField()  # 'windows', etc.
    major_version = IntField()  #  XP=5, Vista, 7, 8, 8.1 = 6
    minor_version = IntField()  #  Vista=6.0, 7=6.1, 8=6.2, 8.1=6.3, 10=10.0
    build_number = IntField()


class ObservedHost(ExtrovirtsDocument):
    fqdn = StringField()
    admins = ListField(ReferenceField('ObservedUser'))
    hostname = StringField()
    dns_domain_name = StringField()
    distinct_fields = [("fqdn",)]
    local_profiles = ListField(ReferenceField('ObservedUser'))
    system_info = StringField()
    processes = ListField(ReferenceField('ObservedProcess'))
    os_version = ReferenceField(ObservedOSVersion)

    def __init__(self, *args, **kwargs):
        if 'hostname' not in kwargs and 'fqdn' in kwargs:
            kwargs['hostname'] = kwargs['fqdn'].split('.')[0]
        if 'dns_domain_name' not in kwargs and 'fqdn' in kwargs:
            kwargs['dns_domain_name'] = '.'.join(kwargs['fqdn'].split('.')[1:])
        super().__init__(*args, **kwargs)


class ObservedFile(ExtrovirtsDocument):
    host = ReferenceField(ObservedHost)
    new_creation_time = StringField()
    new_last_access = StringField()
    new_last_write = StringField()
    old_creation_time = StringField()
    old_last_access = StringField()
    old_last_write = StringField()
    timestomped = BooleanField()
    path = StringField()
    src_host = ReferenceField(ObservedHost)
    src_path = StringField()
    use_case = StringField()  # rat, exfil, observed, modified, collect, dropped
    distinct_fields = [("host", "path", "use_case")]  # If these are the same then


class ObservedShare(ExtrovirtsDocument):
    share_name = StringField() 
    dest_host = ReferenceField(ObservedHost)
    # Todo refactor so that there is another ObservedMountedShare object to represent mounted shares
    share_path = StringField()
    src_host = ReferenceField(ObservedHost)
    mount_point = StringField()


class ObservedUser(ExtrovirtsDocument):
    username = StringField()
    host = ReferenceField(ObservedHost)
    is_group = BooleanField()
    domain = ReferenceField(ObservedDomain)
    sid = StringField()
    distinct_fields = [("sid",), ("host", "username"), ("domain", "username")]


class ObservedCredential(ExtrovirtsDocument):
    found_on_host = ReferenceField(ObservedHost)
    password = StringField()
    user = ReferenceField(ObservedUser)
    hash = StringField()
    distinct_fields = [("user", "password"), ("user", "hash")]


class ObservedSchtask(ExtrovirtsDocument):
    name = StringField()
    host = ReferenceField(ObservedHost)
    status = StringField()
    cred = ReferenceField(ObservedCredential)
    start_time = DateTimeField()
    exe_path = StringField()
    user = ReferenceField(ObservedUser)
    arguments = StringField()
    schedule_type = StringField()


class ObservedService(ExtrovirtsDocument):
    name = StringField()
    host = ReferenceField(ObservedHost)
    start_type = StringField()
    error_control = StringField()  # may or may not care about this
    bin_path = StringField()  # this will include exe parameters
    modifiable_paths = ListField()  # full paths that can be abused (C:\Program.exe for example)
    can_restart = BooleanField()  # can this service be restarted by the user that ran the powerup query
    service_start_name = StringField()  # typically want this to be LocalSystem
    user_context = StringField()  # vulnerability for which user - doesn't apply to all users...
    vulnerability = StringField()  # unquoted, file, bin_path, dll, none
    revert_command = StringField()
    distinct_fields = [("name", "host", "vulnerability")]  # this is how you identify a unique ObservedService


class ObservedTimeDelta(ExtrovirtsDocument):
    seconds = IntField()
    microseconds = IntField()
    host = ReferenceField(ObservedHost)


class ObservedRat(ExtrovirtsDocument):
    host = ReferenceField(ObservedHost)
    elevated = BooleanField()
    executable = StringField()
    username = StringField()
    pid = IntField()


class ObservedRegKey(ExtrovirtsDocument):
    host = ReferenceField(ObservedHost)
    key = StringField()
    path_to_file = StringField()
    value = StringField()
    data = StringField()


class ObservedPersistence(ExtrovirtsDocument):
    host = ReferenceField(ObservedHost)
    user_context = ReferenceField(ObservedUser)
    elevated = BooleanField()
    regkey_artifact = ReferenceField(ObservedRegKey)
    schtasks_artifact = ReferenceField(ObservedSchtask)
    service_artifact = ReferenceField(ObservedService)
    distinct_fields = [('host', 'regkey_artifact'), ('host', 'schtasks_artifact'), ('host', 'service_artifact')]


class ObservedProcess(ExtrovirtsDocument):
    host = ReferenceField(ObservedHost)
    image_name = StringField()
    pid = IntField()
    tid = IntField()
    masked_process = BooleanField()  # mark as true if a pass-the-hash function started this process
    masked_cred = ReferenceField(ObservedCredential)  # the user credential this process is running under, if PTH used
    session_name = StringField()
    session_number = IntField()
    mem_usage = StringField()
    status = StringField()
    username = StringField()
    cpu_time = StringField()
    window_title = StringField()
    modules = StringField()
    services = StringField()
    distinct_fields = [('host', 'image_name', 'pid')]


class Log(ExtrovirtsDocument):
    version = StringField()
    active_operation = DictField()
    active_step = DictField()
    event_stream = ListField(DictField())


class ErrorLog(EmbeddedDocument):
    error = StringField()
    host = StringField()


class IVOB(EmbeddedDocument):
    observed_rat = ReferenceField(ObservedRat)
    rat = ReferenceField(Rat)


class PerformedAction(EmbeddedDocument):
    name = StringField()
    parameters = ListField(DynamicField())


class PerformedStep(EmbeddedDocument):
    name = StringField()
    description = StringField()
    status = StringField()
    jobs = ListField(ReferenceField(Job), default=list)
    params = DictField()
    step = ReferenceField('CodedStep')


class Operation(ExtrovirtsDocument):
    start_time = DateTimeField()
    network = ReferenceField(Network, required=True)
    adversary = ReferenceField("Adversary", required=True)
    performed_actions = EmbeddedDocumentListField(PerformedAction, default=list)
    failed_actions = EmbeddedDocumentListField(PerformedAction, default=list)
    log = ReferenceField(Log, required=True)
    status = StringField(required=True)
    status_state = StringField(required=True)
    name = StringField(required=True)
    parent_process = StringField()
    user_type = StringField()
    start_type = StringField(required=True)
    start_host = ReferenceField(Host, required=True)
    start_user = StringField()
    start_rat = ReferenceField(Rat)
    start_password = StringField()
    start_path = StringField()
    reason = StringField()
    stop_requested = StringField()
    rat_iv_map = EmbeddedDocumentListField(IVOB, default=list)
    known_credentials = ListField(ReferenceField(ObservedCredential), default=list)
    known_domains = ListField(ReferenceField(ObservedDomain), default=list)
    known_files = ListField(ReferenceField(ObservedFile), default=list)
    known_hosts = ListField(ReferenceField(ObservedHost), default=list)
    known_rats = ListField(ReferenceField(ObservedRat), default=list)
    known_schtasks = ListField(ReferenceField(ObservedSchtask), default=list)
    known_shares = ListField(ReferenceField(ObservedShare), default=list)
    known_timedeltas = ListField(ReferenceField(ObservedTimeDelta), default=list)
    known_users = ListField(ReferenceField(ObservedUser), default=list)
    known_persistence = ListField(ReferenceField(ObservedPersistence), default=list)
    known_registry_keys = ListField(ReferenceField(ObservedRegKey), default=list)
    known_services = ListField(ReferenceField(ObservedService, default=list))
    known_processes = ListField(ReferenceField(ObservedProcess), default=list)
    known_os_versions = ListField(ReferenceField(ObservedOSVersion), default=list)
    clean_log = EmbeddedDocumentListField(ErrorLog, default=list)
    steps = ListField(StringField(), default=list)
    planner_facts = StringField()
    jobs = ListField(ReferenceField(Job), default=list)
    performed_steps = EmbeddedDocumentListField(PerformedStep, default=list)
    nonexistent_rats = ListField(ReferenceField(ObservedRat), default=list)
    ignored_rats = ListField(ReferenceField(Rat), default=list)
    object_references = DictField()
    cleanup_index = IntField(default=0)
    perform_cleanup = BooleanField(required=True)
    skip_cleanup = BooleanField()
    delay = IntField(required=True)
    jitter = IntField(required=True)

    def delete(self, *args, **kwargs):
        try:
            self.log.delete()
        except (mongoengine.errors.DoesNotExist, mongoengine.errors.FieldDoesNotExist):
            pass

        delete_fields = ('known_credentials', 'known_domains', 'known_files', 'known_hosts', 'known_rats',
                         'known_schtasks', 'known_shares', 'known_timedeltas', 'known_users', 'known_persistence',
                         'known_registry_keys', 'known_services', 'known_processes',
                         'nonexistent_rats')
        for field in delete_fields:
            for x in getattr(self, field):
                try:
                    x.delete()
                except (mongoengine.errors.DoesNotExist, mongoengine.errors.FieldDoesNotExist):
                    pass

        for job in self.jobs:
                try:
                    if job.status in ("success", "failed"):
                        job.delete()
                except (mongoengine.errors.DoesNotExist, mongoengine.errors.FieldDoesNotExist):
                    pass

        super().delete(*args, **kwargs)


class Term(EmbeddedDocument):
    predicate = StringField()
    literals = ListField(StringField())


class Comparison(EmbeddedDocument):
    obj1 = ListField(StringField())
    comp = StringField()
    obj2 = ListField(StringField())


class CodedStep(ExtrovirtsDocument):
    name = StringField()
    display_name = StringField()
    coded_name = StringField()
    parameters = ListField(StringField())
    score = IntField()
    add = EmbeddedDocumentListField(Term)
    requirement_terms = EmbeddedDocumentListField(Term)
    requirement_comparisons = EmbeddedDocumentListField(Comparison)
    remove = EmbeddedDocumentListField(Term)
    deterministic = BooleanField()
    significant_parameters = ListField(IntField())
    bindings = DictField()
    source_hash = BinaryField()
    summary = StringField()
    mapping = EmbeddedDocumentListField('TechniqueMapping', default=list)
    default_mapping = EmbeddedDocumentListField('TechniqueMapping', default=list)
    cddl = StringField()


class Adversary(ExtrovirtsDocument):
    steps = ListField(ReferenceField(CodedStep, reverse_delete_rule=mongoengine.PULL), default=list)
    name = StringField()
    artifactlists = ListField(ReferenceField(Artifactlist), default=list)
    exfil_method = StringField()
    exfil_address = StringField()
    exfil_port = StringField()
    protected = BooleanField()


class ActiveConnection(ExtrovirtsDocument):
    ip = StringField() # remote host IP
    host = ReferenceField(Host)
    connections = IntField()
    local_ip = StringField()  # local server IP that ip is connected to so we can get specific local interface IP


class AttackTactic(ExtrovirtsDocument):
    name = StringField()
    url = URLField()
    description = StringField()
    order = IntField()


class AttackTechnique(ExtrovirtsDocument):
    tactics = ListField(ReferenceField(AttackTactic))
    technique_id = StringField(unique=True)
    name = StringField()
    description = StringField()
    url = URLField()
    isWindows = BooleanField()
    isMac = BooleanField()
    isLinux = BooleanField()


class AttackGroup(ExtrovirtsDocument):
    name = StringField()
    group_id = StringField(unique=True)
    url = URLField()
    aliases = ListField(StringField())
    techniques = ListField(ReferenceField(AttackTechnique))


class AttackList(ExtrovirtsDocument):
    master_list = StringField()


class TechniqueMapping(EmbeddedDocument):
    tactic = ReferenceField(AttackTactic)
    technique = ReferenceField(AttackTechnique)


class Setting(ExtrovirtsDocument):
    last_attack_update = DateTimeField()
    last_psexec_update = DateTimeField()
    recursion_limit = IntField()
