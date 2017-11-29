from .command import CommandLine
from typing import List, Callable, Tuple, NamedTuple
from . import parsers
import datetime


def tasklist(args: List[str]=None) -> CommandLine:
    """
    The net command is one of Windows' many swiss army knives.

    Args:
        args: Additional command line arguments to net.exe
    """

    command_line = ['tasklist']
    if args:
        command_line += args

    return CommandLine(command_line)


def main(verbose: bool=False, services: bool=False, modules: bool=False, remote_host: str=None, user: str=None,
        password: str = None, user_domain: str=None) -> Tuple[CommandLine, Callable[[str], List[NamedTuple]]]:

    args = ['/FO CSV']

    if remote_host:
        args.append("/S " + remote_host)

        if user:
            args.append("/U " + ((user_domain + '\\' + user) if user_domain else user))

        if password:
            args.append("/p " + password)

    if verbose:
        args += ['/V']

    if services:
        args += ['/SVC']

    if modules:
        args += ['/M']

    return tasklist(args), parsers.tasklist.csv_with_headers


