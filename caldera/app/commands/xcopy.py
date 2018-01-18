from .command import CommandLine
from typing import List, Tuple


def xcopy(args: List[str], overwrite_destination: bool) -> CommandLine:
    """Copies files and directories, including subdirectories.
    Ref: https://technet.microsoft.com/en-us/library/bb491035.aspx

    Args:
        args: Additional command line arguments to xcopy.exe
        overwrite_destination: True means overwrite the destination if it already exists.

    Returns:
        The CommandLine
    """
    if overwrite_destination:
        args.append('/y')

    return CommandLine(args)


def file(source: str, destination: str, overwrite_destination: bool=False) -> Tuple[CommandLine, None]:
    """Creates an xcopy command. By default xcopy will prompt whether the destination name is a file or directory.
    This pipes a response into the Xcopy process to avoid needing to interact with it directly.

    Args:
        source: The source path of the file to copy
        destination: The destination path to place the file
        overwrite_destination: True if the destination should be overwritten if it already exists

    Returns:
        The CommandLine and a parser for the output of the command
    """
    args = ['cmd.exe /c echo F | xcopy', source, destination]

    # return xcopy(args), parsers.xcopy.main
    return xcopy(args, overwrite_destination), None


def folder(source: str, destination: str, overwrite_destination: bool=False) -> Tuple[CommandLine, None]:
    # This function has not been tested.
    raise NotImplementedError
    args = ['cmd.exe /c echo D | xcopy', source, destination]

    # return xcopy(args), parsers.xcopy.main
    return xcopy(args, overwrite_destination), None

