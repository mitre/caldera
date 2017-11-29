from .command import CommandLine
from typing import List


def runas(user: str, program: str, args: List[str]=None) -> CommandLine:
    """
    The net command is one of Windows' many swiss army knives.

    :type context: ExecutionContext
    :param args: Additional command line arguments to net.exe
    :return:
    """

    command_line = ['runas.exe']
    if args:
        command_line += args

    return CommandLine(command_line)
