from typing import Union, List


class CommandLine(object):
    """This represents a command line that can be executed.

    The actual string representing the command is stored in the variable ``command_line``.
    """
    def __init__(self, command_line: Union[str, List[str]]=None):
        """Creates a CommandLine.

        Args:
            command_line: The commandline. Can be a string, in which case the string is used directly as the command, or
                a list of strings, in which case the list is join together with the space character to create the
                final command.
        """

        if command_line and isinstance(command_line, list):
            command_line = ' '.join(command_line)
        self.command_line = command_line
