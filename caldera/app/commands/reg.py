from .command import CommandLine
from typing import List, Callable, Tuple
from . import parsers


def reg(remote_host: str=None, args: List[str]=None) -> CommandLine:
    """
    The reg command is used to query and modify the Windows registry.

    Args:
        context: ExecutionContext
        remote_host: The host that is the target of the reg operation
        args: Additional command line arguments to reg.exe
    """

    command_line = ['reg']

    if remote_host is not None:
        command_line += "\\\\{}".format(remote_host)

    if args:
        command_line += args

    return CommandLine(command_line)


def query(remote_host: str=None, key: str=None, value: str=None, switches: List[str]=None) \
        -> Tuple[CommandLine, Callable[[str], List[str]]]:
    """
    Args:
        remote_host: (Optional) The remote host on which to run the command
        key: The key e.g. HKLM\Software\Windows
        value: The value of to be queried
        switches: (Optional) Switches to add to command
    """
    args = ["query", key]
    if switches:
        args += switches

    return reg(remote_host=remote_host, args=args), parsers.reg.query


def add(remote_host: str=None, key: str=None, value: str=None, data: str=None, force: bool=False) \
        -> Tuple[CommandLine, Callable[[str], None]]:

    args = ['add', key, "/v " + value, "/d " + data]

    if force:
        args += ["/f"]

    return reg(remote_host=remote_host, args=args), parsers.reg.add


def load(remote_host: str=None, key: str=None, file: str=None) -> Tuple[CommandLine, Callable[[str], None]]:

    args = ["load", key, file]

    return reg(remote_host=remote_host, args=args), parsers.reg.load


def unload(remote_host: str=None, key: str=None) -> Tuple[CommandLine, Callable[[str], None]]:

    args = ["unload", key]

    return reg(remote_host=remote_host, args=args), parsers.reg.unload


def delete(remote_host: str=None, key: str=None, value: str=None, force: bool=False) \
        -> Tuple[CommandLine, Callable[[str], None]]:

    args = ["delete", key]

    if value:
        args += ["/v " + value]

    if force:
        args += ["/f"]

    return reg(remote_host=remote_host, args=args), parsers.reg.delete
