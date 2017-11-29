from .command import CommandLine
from typing import List, Tuple, Callable
from . import parsers


def wmic(args: List[str]=None) -> CommandLine:
    """
    Wrapper for the windows tool wmic.exe

    Args:
        args: The additional arguments for the command line
    """
    command_line = ["wmic"]

    if args is not None:
        command_line += args

    return CommandLine(command_line)


def create(exe_path: str, arguments: str=None, remote_host: str=None, user: str=None, user_domain: str=None,
           password: str=None) -> Tuple[CommandLine, Callable[[str], None]]:
    """
    Perform a remote process create with wmic

    Args:
        exe_path: The path to the program that will be run
        arguments: The commandline arguments to the running program
        remote_host: The host on which the program wil be run
        user: The username of the user whose credentials will be used to authenticate with the remote_host
        user_domain: The (Windows) domain of the user
        password: The password of the user account that will be used to authenticate to the remote_host
    """
    if '-' in remote_host:
        remote_host = '"' + remote_host + '"'
    args = ["/node:" + remote_host]

    args.append("/user:\"{}\\{}\"".format(user_domain, user))

    args.append("/password:\"{}\"".format(password))

    args += ["process", "call", "create"]

    args.append('"{} {}"'.format(exe_path, arguments))

    return wmic(args), parsers.wmic.create
