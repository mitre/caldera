from .util import tz_utcnow
import uuid
from typing import List, Tuple
from .engine.objects import Log


version = "1.0"


class Operation(dict):
    def __init__(self):
        super().__init__()
        self['id'] = str(uuid.uuid4())
        self['steps'] = []
        self['nodetype'] = 'operation'


class AttackReference(dict):
    def __init__(self, technique_id, technique_name, tactics):
        super().__init__()
        self['technique_id'] = technique_id
        self['technique_name'] = technique_name
        self["tactic"] = tactics


class Step(dict):
    def __init__(self, attack_info: List[AttackReference]):
        super().__init__()
        self['id'] = str(uuid.uuid4())
        self['nodetype'] = 'step'
        self['attack_info'] = attack_info
        self['events'] = []


class Event(dict):
    def __init__(self, obj, action, host, start_time=None, fields=None):
        if start_time is None:
            start_time = tz_utcnow()
        if fields is None:
            fields = {}
        super().__init__()
        self['id'] = str(uuid.uuid4())
        self['nodetype'] = 'event'
        self['host'] = host
        self['object'] = obj
        self['action'] = action
        self['happened_after'] = start_time
        self.update(**fields)

    def end(self, successful):
        self['happened_before'] = tz_utcnow()
        # self['successful'] = successful
        if not successful:
            return None

        return self


class ProcessEvent(Event):
    def __init__(self, host, ppid, pid, command_line, action='create'):
        args = {'fqdn': host,
                'ppid': ppid,
                'pid': pid,
                'command_line': command_line}
        super().__init__("process", action, host, fields=args)


class FileEvent(Event):
    def __init__(self, fqdn, file_path, action='create'):
        args = {'fqdn': fqdn,
                'file_path': file_path}
        super().__init__('file', action, fqdn, fields=args)


class CredentialDump(Event):
    def __init__(self, fqdn, pid, typ, usernames):
        args = {'fqdn': fqdn,
                'pid': pid,
                'type': typ,
                'usernames': usernames}
        super().__init__('cred', 'dump', fqdn, fields=args)


class RegistryEvent(Event):
    def __init__(self, fqdn, key, data, value, action="add"):
        args = {'fqdn': fqdn,
                'key': key,
                'value': value,
                'data': data}
        super().__init__('registry', action, fqdn, fields=args)


class ProcessOpen(Event):
    def __init__(self, fqdn, file_path, actor_pid):
        args = {'fqdn': fqdn,
                'file_path': file_path,
                'actor_pid': actor_pid}
        super().__init__('process', 'open', fqdn, fields=args)


class BSFEmitter(object):
    def __init__(self, log: Log):
        """
        An object that handles emitting BSF events
        Args:
            log: the log to emit log entries to
        """
        self.log = log

    def start_operation(self):
        self.log.modify(active_operation=Operation())

    def add_step(self, step: Step):
        if self.log.active_step and len(self.log.active_step['events']) > 0:
            self.log.modify(push__event_stream=self.log.active_step)

        self.log.modify(push__active_operation__steps=step['id'])
        self.log.modify(active_step=step)

    def add_event(self, event):
        if not isinstance(event, CredentialDump):
            self.log.modify(push__active_step__events=event['id'])
            self.log.modify(push__event_stream=event)

    def done(self):
        if self.log.active_step:
            self.log.modify(push__event_stream=self.log.active_step)

        if self.log.active_operation:
            self.log.modify(push__event_stream=self.log.active_operation)
