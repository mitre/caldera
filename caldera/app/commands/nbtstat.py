from .command import CommandLine
from typing import List, Callable, Tuple
from . import parsers


def nbtstat(args: List[str]=None) -> CommandLine:
    """
    The nbtstat command is one of Windows' many swiss army knives.

    Args:
        args: Additional command line arguments to nbtstat.exe
    """

    command_line = ['nbtstat']
    if args:
        command_line += args

    return CommandLine(command_line)


def n() -> Tuple[CommandLine, Callable[[str], str]]:
    """
    Create a call to nbtstat -n

    Returns:
        Returns the CommandLine and a parser for the Commandline
    """
    return nbtstat(['-n']), parsers.nbtstat.n
