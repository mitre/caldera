from .command import CommandLine
from typing import List, Callable, Tuple, NamedTuple, Union
from . import parsers


def tasklist(args: List[str]=None) -> CommandLine:
    """Commandline wrapper for the windows tasklist command.

    Args:
        args: Additional command line arguments

    Returns:
        The CommandLine
    """

    command_line = ['tasklist']
    if args:
        command_line += args

    return CommandLine(command_line)


def main(verbose: bool=False, services: bool=False, modules: bool=False, remote_host: Union[None, str]=None,
         user: Union[None, str]=None, password: Union[None, str]=None, user_domain: Union[None, str]=None) -> \
        Tuple[CommandLine, Callable[[str], List[NamedTuple]]]:
    """Create a tasklist command

    Args:
        verbose: If ``True`` runs tasklist in verbose mode (the "/V" flag)
        services: If ``True`` lists services in each process (the "/SVC" flag)
        modules: If ``True`` lists the modules loaded in each process (the "/M" flag)
        remote_host: The system to list the process of, or ``None`` to list the processes on the local computer
            (the "/S" flag)
        user: The user name that the command should execute under (the "/U" flag)
        password: The password of the user, required if the `user` argument is provided. (the "/P" flag)
        user_domain: The Windows name for the domain of the user

    Returns:
        The generated CommandLine and a parser for the output of this command

    """

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


