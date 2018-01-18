from .command import CommandLine
from typing import List, Callable, Tuple
from . import parsers


def reg(remote_host: str=None, args: List[str]=None) -> CommandLine:
    """
    The reg command is used to query and modify the Windows registry.

    Args:
        remote_host: The host that is the target of the reg operation
        args: Additional command line arguments to reg.exe

    Returns:
        The CommandLine
    """

    command_line = ['reg']

    if remote_host is not None:
        command_line += "\\\\{}".format(remote_host)

    if args:
        command_line += args

    return CommandLine(command_line)


def query(remote_host: str=None, key: str=None, value: str=None, switches: List[str]=None) \
        -> Tuple[CommandLine, Callable[[str], List[str]]]:
    """Build a command to read a value from the registry using "reg query"

    Args:
        remote_host: (Optional) The remote host on which to run the command, or `None` for local execution
        key: The key e.g. ``HKLM\\Software\\Windows``
        value: The value of the key to be queried, or `None` to query all values
        switches: (Optional) Switches to add to command

    Returns:
        The CommandLine and a parser for the output of the command
    """
    args = ["query", key]

    if value:
        args.extend(['/v', value])

    if switches:
        args += switches

    return reg(remote_host=remote_host, args=args), parsers.reg.query


def add(remote_host: str=None, key: str=None, value: str=None, data: str=None, force: bool=False) \
        -> Tuple[CommandLine, Callable[[str], None]]:
    """Build a command to add a value to the registry using "reg add"

    Args:
        remote_host: (Optional) The remote host on which to run the command, or `None` for local execution
        key: The key e.g. ``HKLM\\Software\\Windows``
        value: The value of the key to be added
        data: The data to put in the registry
        force: `True` to use the force flag ("/f")

    Returns:
        The CommandLine and a parser for the output of the command
    """

    args = ['add', key, "/v " + value, "/d " + data]

    if force:
        args += ["/f"]

    return reg(remote_host=remote_host, args=args), parsers.reg.add


def load(remote_host: str=None, key: str=None, file: str=None) -> Tuple[CommandLine, Callable[[str], None]]:
    """Build a command to load a hive file into the registry using "reg load"

    Args:
        remote_host: (Optional) The remote host on which to run the command, or `None` for local execution
        key: The key to load the hive file at e.g. ``HKLM\\TempHive``
        file: The path to the hive file

    Returns:
        The CommandLine and a parser for the output of the command
    """
    args = ["load", key, file]

    return reg(remote_host=remote_host, args=args), parsers.reg.load


def unload(remote_host: str=None, key: str=None) -> Tuple[CommandLine, Callable[[str], None]]:
    """Build a command to unload a hive file from the registry using "reg unload"

    Args:
        remote_host: (Optional) The remote host on which to run the command, or `None` for local execution
        key: The key of the hive to unload e.g. ``HKLM\\TempHive``

    Returns:
        The CommandLine and a parser for the output of the command
    """
    args = ["unload", key]

    return reg(remote_host=remote_host, args=args), parsers.reg.unload


def delete(remote_host: str=None, key: str=None, value: str=None, force: bool=False) \
        -> Tuple[CommandLine, Callable[[str], None]]:
    """Build a command to delete a registry value using "reg delete"

    Args:
        remote_host: (Optional) The remote host on which to run the command, or `None` for local execution
        key: The key to delete e.g. ``HKLM\\TempHive``
        value: (Optional) The value to be deleted. Or `None` to delete the entire ``key``
        force: `True` to use the force flag ("/f")

    Returns:
        The CommandLine and a parser for the output of the command
    """

    args = ["delete", key]

    if value:
        args += ["/v " + value]

    if force:
        args += ["/f"]

    return reg(remote_host=remote_host, args=args), parsers.reg.delete
