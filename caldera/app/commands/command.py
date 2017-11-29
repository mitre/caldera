from typing import Union, List


class CommandLine(object):
    def __init__(self, command_line: Union[str, List[str]] = None):
        if command_line and isinstance(command_line, list):
            command_line = ' '.join(command_line)
        self.command_line = command_line
