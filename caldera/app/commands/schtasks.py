from .command import CommandLine
from typing import List, Union, Callable, Tuple
import datetime as datetime_mod
from . import parsers


def schtasks(args: List[str]=None) -> CommandLine:
    """
    Wrapper for the windows tool sc.exe

    Args:
        args: The additional arguments for the command line
    """
    command_line = ["schtasks"]

    if args is not None:
        command_line += args

    return CommandLine(command_line)


def create(task_name: str, exe_path: str, arguments: Union[str, List[str]]=None, remote_host: str=None,
           remote_user: str=None, remote_password: str=None, user: str=None, user_domain: str=None,
           password: str=None, start_time: datetime_mod.datetime=None, schedule_type: str=None) \
        -> Tuple[CommandLine, Callable[[str], None]]:
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

    if ' ' in exe_path:
        exe_path = "\"'{}'\"".format(exe_path)

    if len(arguments) > 0:
        exe_path = "\"{} {}\"".format(exe_path, arguments)

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
