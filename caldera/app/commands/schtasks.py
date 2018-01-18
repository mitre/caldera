from .command import CommandLine
from typing import List, Union, Callable, Tuple
import datetime as datetime_mod
from . import parsers


def schtasks(args: List[str]=None) -> CommandLine:
    """Wrapper for the windows tool schtasks.exe

    Args:
        args: The additional arguments for the command line

    Returns:
        The CommandLine
    """
    command_line = ["schtasks"]

    if args is not None:
        command_line += args

    return CommandLine(command_line)


def create(task_name: str, exe_path: str, arguments: Union[str, List[str]]=None, remote_host: str=None,
           remote_user: str=None, remote_password: str=None, user: str=None, user_domain: str=None,
           password: str=None, start_time: datetime_mod.datetime=None, schedule_type: str=None) \
        -> Tuple[CommandLine, Callable[[str], None]]:
    """Create a scheduled task using "schtasks".

    Args:
        task_name: The name of the task (the "/TN" flag)
        exe_path: The path to the executable for the task. If the task is being scheduled on another computer this is
            the path relative to that computer. (combined with the arguments to form the "/TR" flag)
        arguments: Any arguments to be passed to the executable when it is run within the task (combined with the
            exe_path to form the "/TR" flag)
        remote_host: The host that the task will be scheduled on (the "/RU" flag)
        remote_user: The user account that the task will execute under. Often this is "System" (the "/RP" flag)
        remote_password: The password for the remote_user account. Leave blank if the remote user is "System"
            (the "/RU" flag)
        user: The user account to authenticate with when creating this scheduled tasks (if different from the current
            user context).
        user_domain: The domain for the ``user`` (combined with ``user`` to form the "/U" flag)
        password: The password for the ``user`` (the "/P" flag)
        start_time: The time that the task is scheduled to run at (the "/ST" and "/SD" flags)
        schedule_type: The schedule type (the "/SC" flag). One of (MINUTE, HOURLY, DAILY, WEEKLY,
                       MONTHLY, ONCE, ONSTART, ONLOGON, ONIDLE, ONEVENT). If ``None`` is passed, will use "ONCE".

    Returns:
        The CommandLine and a parser for the command

    """
    args = ['/Create']

    if remote_host is not None:
        args.append('/S ' + remote_host)
        if user is not None:
            if user_domain is not None:
                 args.append('/U ' + user_domain + '\\' + user)
            else:
                 args.append('/U ' + user)
            if password is not None:
                args.append('/P ' + password)

    if schedule_type:
        args.append('/SC ' + schedule_type)
    else:
        args.append('/SC ONCE')

    args.append('/TN ' + task_name)

    if arguments is not None and isinstance(arguments, list):
        arguments = ' '.join(["'{}'".format(x) if ' ' in x else x for x in arguments])

    double_quote = False
    if ' ' in exe_path:
        exe_path = "'{}'".format(exe_path)
        double_quote = True

    if arguments:
        exe_path = "{} {}".format(exe_path, arguments)
        double_quote = True

    if double_quote:
        exe_path = '"{}"'.format(exe_path)

    args.append('/TR ' + exe_path)

    if start_time is not None:
        args.append('/ST ' + start_time.strftime('%H:%M'))
        args.append('/SD ' + start_time.strftime('%m/%d/%Y'))

    args.append("/F")

    if remote_user is not None:
        args.append('/RU ' + remote_user)
        if remote_password is not None:
            args.append('/RP ' + remote_password)

    return schtasks(args=args), parsers.schtasks.create


def delete(task_name: str, remote_host: str=None, user: str=None, user_domain: str=None, password: str=None,
           force: bool=False) -> Tuple[CommandLine, Callable[[str], None]]:
    """Create a command that will delete a scheduled task.

    Args:
        task_name: The task that will be deleted (the "/TN" flag).
        remote_host: The host to remove the task from, if different from the local host (the "/S" flag)
        user: The user account to authenticate with when delteing this scheduled tasks (if different from the current
            user context).
        user_domain: The domain for the ``user`` (combined with ``user`` to form the "/U" flag)
        password: The password for the ``user`` (the "/P" flag)
        force: Whether to Force delete (the "/F" flag)

    Returns:
        The generated CommandLine and a parser for the command
    """

    args = ['/Delete', '/TN ' + task_name]

    if remote_host is not None:
        args.append('/S ' + remote_host)
        if user is not None:
            if user_domain is not None:
                args.append('/U ' + user_domain + '\\' + user)
            else:
                args.append('/U ' + user)
            if password is not None:
                args.append('/P ' + password)

    if force:
        args.append('/F')

    return schtasks(args=args), parsers.schtasks.delete
