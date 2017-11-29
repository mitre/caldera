from .command import CommandLine
from typing import List


def at(remote_host: str=None, args: List[str]=None) -> CommandLine:
    """
    The net command is one of Windows' many swiss army knives.
    Args:
        remote_host: The host that is the target of the at command
        args: Additional command line arguments to net.exe
    """

    command_line = ['at']

    if remote_host:
        args.append('\\' + remote_host)

    if args:
        command_line += args

    return CommandLine(command_line)


def enum(remote_host: str=None) -> CommandLine:
    """
    :param remote_host: (Optional) The remote host on which to run the command
    """
    return at(remote_host=remote_host)


def create(time: str=None, command_line: str=None, remote_host: str=None) -> CommandLine:
    args = []
    if time:
        args.append(time)

    args.append(command_line)
    return at(remote_host=remote_host, args=args)
