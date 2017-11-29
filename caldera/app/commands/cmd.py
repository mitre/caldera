from .command import CommandLine
from typing import Callable, Tuple, Union
from . import parsers, errors
import types


def copy(src_file_path: str, dst_file_path: str) -> Tuple[CommandLine, Callable[[str], None]]:
    """
    Copies a file using the copy command built in to cmd.exe

    Args:
        src_file_path: The source path of the file that will be copied
        dst_file_path: The destination path of the file that will be copied

    Returns:
        The CommandLine and a parser for the output of the command
    """
    return CommandLine('cmd /c copy \"{}\" \"{}\"'.format(src_file_path, dst_file_path)), parsers.cmd.copy


def shutdown(reboot: bool, delay: int, force: bool) -> Tuple[CommandLine, Callable[[str], None]]:
    """
    Issues the command to shutdown the current computer, possibly for reboot

    Args:
        reboot: boolean if the shutdown should reboot
        delay: how long the computer should wait until starting to shutdown
        force: boolean if the computer should force close all open programs or prompt user for input

    Return:
        The CommandLine (no parser because the box should be rebooting)
    """
    args = ['shutdown', '/t', str(delay)]
    if reboot:
        args.append('/r')
    if force:
        args.append('/f')
    command = ' '.join(args)
    return CommandLine('cmd /c {}'.format(command)), parsers.shutdown.shutdown


def move(src_file_path: str, dst_file_path: str, suppress_overwrite: bool) -> Tuple[CommandLine, Callable[[str], None]]:
    """
    move is the "move" command that moves a file

    Args:
         src_file_path: path of current file
         dst_file_path: path where the new file will be
         suppress_overwrite: bool to overwrite a file if it already exists
    """
    args = ['move']
    if suppress_overwrite:
        args.append('/Y')
    command = ' '.join(args)
    return CommandLine('cmd /c {} \"{}\" \"{}\"'.format(command, src_file_path, dst_file_path)), parsers.cmd.move


def delete(path: str) -> Tuple[CommandLine, Callable[[str], None]]:
    """
    delete is the "del" command that deletes a file

    Args:
        path: the path of the file to be deleted
    """
    args = ['cmd /c del', "\"" + path + "\""]

    return CommandLine(args), parsers.cmd.delete


def dir_list(search: Union[str, list], b: bool, s: bool, a: str) -> Tuple[CommandLine, Callable[[str], None]]:
    """
    dir_list is the "dir" command that lists the files/folders in a directory

    Args:
        search: what to list, can either be a single full path (str) or can be a list of things to search for
                within the current working directory (list)
        b: bool on if we should include the /b flag in the query (bare info, just filename)
        s: bool on if we should include the /s flag in the query (recursive)
        a: potential arguments to include with the /a flag if a is not None
    """
    args = ["cmd /c dir"]
    if isinstance(search, str):
        args.append("\"" + search + "\"")  # this is the instance where you do dir C:\
    else:
        for word in list:
            args.append("*" + word + "*")  # this is the instance where you do dir *test* *files*
    if b:
        args.append('/b')
    if s:
        args.append('/s')
    if a is not None:
        args.append('/a' + a)
    # outputs of these different switches is radically different, so need different parsers for the different versions
    if b and s:
        return CommandLine(args), parsers.cmd.dir_collect
    else:
        raise errors.ParserNotImplementedError


def powershell(command: str) -> Tuple[CommandLine, Callable[[str], None]]:
    """
    Runs a Powershell query through the Windows command prompt.

    Args:
        command: the PowerShell command to run. Remmeber that you can separate multiple PowerShell commands with ;
    """
    ps_command = "powershell -ExecutionPolicy Bypass -WindowStyle Minimized -Command "+command

    return CommandLine('cmd /c \"{}\""'.format(ps_command)), parsers.cmd.powershell