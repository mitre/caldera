from .command import CommandLine
from typing import List, Tuple, Callable
from . import parsers


def xcopy(args: List[str]=None, copying_file: bool=True) -> CommandLine:
    """
    Xcopy - Copies files and directories, including subdirectories.
    Ref: https://technet.microsoft.com/en-us/library/bb491035.aspx

    Args:
        args: Additional command line arguments to net.exe
        copying_file: Defaults to True.  True means that we're intending to copy a file.
    """

    if copying_file:
        # Invoking xcopy as follows tells it that it's copying a file without needing to interact with the prompt.
        # However, this method means that we don't get any output to check if it's successful.
        command_line = ['cmd.exe /c echo F | xcopy']
    else:  # We're copying a directory
        command_line = ['cmd.exe /c echo D | xcopy']

    if args:
        command_line += args

    return CommandLine(command_line)


def main(source: str, destination: str, overwrite_destination: bool=False, copying_file: bool=True) \
        -> Tuple[CommandLine, None]:
    args = [source, destination]

    if overwrite_destination:
        args.append('/y')

    # return xcopy(args), parsers.xcopy.main
    return xcopy(args), None


def file(*args: List[str], **kwargs) -> Tuple[CommandLine, None]:
    """ By Xcopy will prompt whether the destination name is a file or directory. This pipes a response into the
    Xcopy process to avoid needing to interact with it directly. """
    return main(*args, **kwargs, copying_file=True)


def folder(*args: List[str], **kwargs) -> Tuple[CommandLine, None]:
    # This function has not been tested.
    raise NotImplementedError
    return main(*args, **kwargs, copying_file=False)


