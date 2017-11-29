from .command import CommandLine
from typing import List


def makecab(path: str=None, args: List[str]=None) -> CommandLine:
    """
    Makes a cabinet file

    Args:
        path: path to the cabinet file
        args: Additional command line arguments to net.exe
    """

    command_line = ['makecab']

    command_line += " " + path

    if args:
        command_line += args

    return CommandLine(command_line)
