from .command import CommandLine
from typing import Union, Callable


def escape_string(text: str, escape_dollarsign=True):
    dquote = False
    if '`' in text:
        text = text.replace('`', '``')
        dquote = True
    if '#' in text:
        text = text.replace('#', '`#')
        dquote = True
    if "'" in text:
        text = text.replace("'", "`'")
        dquote = True
    if '"' in text:
        text = text.replace('"', '`"')
        dquote = True
    if escape_dollarsign and '$' in text:
        text = text.replace('$', '`$')
        dquote = True

    if " " in text or dquote:
        return '"{}"'.format(text)
    else:
        return text


class PSArg(object):
    def __init__(self, argname: str, argval: Union[str, CommandLine]=None, escape: Union[None, Callable]=escape_string):
        if isinstance(argval, CommandLine):
            argval = argval.command_line
        if argval and escape:
            argval = escape(argval)

        self.text = "-{} {}".format(argname, argval)


class PSFunction(object):
    def __init__(self, function_name: str, *args: PSArg) -> None:
        self.command = [function_name]

        for arg in args:
            self.command.append(arg.text)

        self.command = CommandLine(self.command)


def escape_string_literally(text: str):
    text = text.replace("'", "''")
    return "'{}'".format(text)
