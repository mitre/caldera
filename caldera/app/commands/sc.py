from .command import CommandLine
from typing import List, Tuple, Callable
from . import parsers


def sc(args: List[str]=None, remote_host: str=None) -> CommandLine:
    """
    Wrapper for the windows tool sc.exe

    Args:
        args: The additional arguments for the command line
        remote_host: Optional - run on a remote host via RPC.
    """
    command_line = ["sc.exe"]

    if remote_host is not None:
        command_line.append('\\\\' + remote_host)

    if args is not None:
        command_line += args

    return CommandLine(command_line)


def create(path: str=None, name: str=None, remote_host: str=None) -> Tuple[CommandLine, Callable[[str], None]]:
    """
    Gain persistence and privilege escalation by installing a service.

    Args:
        path: Path to the binary (binPath)
        name: Name of the service (svcName)
        remote_host:  Optional - IP or hostname of remote host
    """
    args = ['create', name, 'binPath= ' + path, 'start= auto']

    return sc(args=args, remote_host=remote_host), parsers.sc.create


def start(name: str=None, remote_host: str=None) -> Tuple[CommandLine, Callable[[str], None]]:
    """
    Gain privileged execution by starting a service (locally or remotely).

    Args:
        name: Name of the service (svcName)
        remote_host:  Optional - IP or hostname of remote host
    """
    args = ['start', name]

    return sc(args=args, remote_host=remote_host), parsers.sc.start


def stop(name: str=None, remote_host: str=None) -> Tuple[CommandLine, Callable[[str],None]]:
    """
    Stop a running service so that it can be modified

    Args:
         name: Name of the service
         remote_host: Optional - IP or hostname of remote host
    """
    args = ['stop', name]
    return sc(args=args, remote_host=remote_host), parsers.sc.stop


def query(name: str=None, remote_host: str=None) -> Tuple[CommandLine, Callable[[str], None]]:
    """
    Gain privileged execution by starting a service (locally or remotely).

    Args:
        name: Name of the service (svcName)
        remote_host:  Optional - IP or hostname of remote host
    """
    args = ['query']
    if name:
        args.append(name)

    return sc(args=args, remote_host=remote_host), parsers.sc.query


def delete(name: str=None, remote_host: str=None) -> Tuple[CommandLine, Callable[[str], None]]:
    """
    Remove a service. Used to revert from sc_create.

    Args:
        name: Name of the service (svcName)
        remote_host:  Optional - IP or hostname of remote host
    """
    args = ['delete', name]

    return sc(args=args, remote_host=remote_host), parsers.sc.delete


def config(name: str=None, remote_host: str=None, bin_path: str=None, start_name: str=None, password: str=None) -> Tuple[CommandLine, Callable[[str],None]]:
    """
    Modify a service. Used primarily for privilege escalation and lateral movement.

    Args:
        name: Name of the service (svcName)
        remote_host: Optional - IP or hostname of the remote host
        bin_path: Optional - new binary path + args to use
        start_name: Optional - new user to start as (default service name is LocalSystem)
        password: Optional - should be set if start_name is anything other than LocalSystem
                            except for things like "NT AUTHORITY\LocalService"
    Return:
        Tuple of commandline string to run and a parser for the output of the command line
    """
    args = ["config", name]
    if bin_path:
        args.append("binPath= " + bin_path)
    if start_name:
        args.append("obj= " + start_name)
        if password:
            args.append("password= " + password)

    return sc(args=args, remote_host=remote_host), parsers.sc.config
