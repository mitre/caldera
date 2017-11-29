from .command import CommandLine
from typing import List, Tuple, Callable
from . import parsers


def taskkill(args: List[str]=None) -> CommandLine:
    """
    Wrapper for the windows tool taskkill.exe

    Args:
        args: The additional arguments for the command line
    """
    command_line = ["taskkill"]

    if args is not None:
        command_line += args

    return CommandLine(command_line)


def by_image(exe_name) -> Tuple[CommandLine, Callable[[str], None]]:
    """
    Taskkill by image name

    Args:
        exe_name: Name of the process to kill, the file name including '.exe' extension
    """
    args = ['/im', exe_name, '/f']

    return taskkill(args), parsers.taskkill.taskkill


def by_pid(pid: int) -> Tuple[CommandLine, Callable[[str], None]]:
    """
    Taskkill by pid

    Args:
        pid: The pid of the process to kill
    """
    args = ['/pid', str(pid), '/f']

    return taskkill(args), parsers.taskkill.taskkill
