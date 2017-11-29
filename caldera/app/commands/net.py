from .command import CommandLine
from typing import List, Callable, Tuple
from . import parsers
import datetime


def net(args: List[str]=None) -> CommandLine:
    """
    The net command is one of Windows' many swiss army knives.

    Args:
        args: Additional command line arguments to net.exe
    """

    command_line = ['net']
    if args:
        command_line += args

    return CommandLine(command_line)


def use(remote_host: str, remote_share: str, device: str=None, remote_volume: str=None, user: str=None,
        user_domain: str=None, password: str=None) -> Tuple[CommandLine, Callable[[str], None]]:
    """
    Net use will mount a network share on this host

    Args:
        device: The local drive letter that the share will be mapped to
        remote_host: The remote computer
        remote_share: The remote share
        remote_volume: (Optional) The remote volume
        user: (Optional) The remote credential to be used
        password: (Optional) The password to be used
        user_domain: The (Windows) domain of the user account
    Returns:
        The CommandLine and a parser
    """
    args = ['use']

    if device is not None:
        args.append(device)

    args.append('\\\\{}\\{}'.format(remote_host, remote_share))

    if remote_volume is not None:
        args[1] += '\\' + remote_volume

    if user is not None:
        if password is not None:
            args.append(password)
        if user_domain is not None:
            args.append('/user:' + user_domain + '\\' + user)
        else:
            args.append('/user:' + user)

    return net(args=args), parsers.net.use


def time(remote_host: str=None) -> Tuple[CommandLine, Callable[[str], datetime.datetime]]:
    """
    Gets the time of a remote host

    Args:
        remote_host: The host that time will be checked on

    Returns:
        A CommandLine, and a parser for the command
    """
    args = ['time']

    if remote_host is not None:
        args.append('\\\\' + remote_host)

    return net(args=args), parsers.net.time


def use_delete(remote_host: str, remote_share: str) -> Tuple[CommandLine, Callable[[str], None]]:
    """
    Net use delete will unmount a network share on this host

    Args:
        remote_host: The remote computer
        remote_share: The remote share
    """
    args = ['use',
            '\\\\{}\\{}'.format(remote_host, remote_share),
            '/delete']

    return net(args=args), parsers.net.use_delete
