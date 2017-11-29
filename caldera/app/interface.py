import base64
from typing import Union

from .engine.objects import Job, Host, Rat, Opcodes
from . import powershell
from .commands.powershell import PSArg, PSFunction
from .commands.command import CommandLine


#
# Rat Commands
#
def send_shell_command(rat: Rat, cmd: str) -> Job:
    return Job.create_rat_command(rat, Opcodes.EXECUTE, command_line=cmd)


def exfil_network_connection(rat: Rat, addr: str, port: str, file_path: str, method: str) -> Job:
    return Job.create_rat_command(rat, Opcodes.EXFIL_CONNECTION, address=addr, port=port,
                                  file_path=file_path, method=method)


def drop_file(rat: Rat, file_path: str, contents: bytes):
    return Job.create_rat_command(rat, Opcodes.WRITE_FILE, file_path=file_path,
                                  contents=base64.encodebytes(contents).decode('utf-8'))


def powershell_function(rat: Rat, script_anchor: str, command: PSFunction) -> Job:
    stdin = "[[" + script_anchor + "]] " + command.command.command_line
    return Job.create_rat_command(rat, Opcodes.EXECUTE, command_line=powershell.PS_COMMAND, stdin=stdin)


def invoke_reflective_pe_injection(rat: Rat, binary_name: str, command: CommandLine):
    anchor = "reflectivepe.{}".format(binary_name)
    # command = 'Invoke-ReflectivePEInjection -PEBytes $DecodedPE -ExeArgs "{}"'.format(command)
    command = PSFunction('Invoke-ReflectivePEInjection', PSArg('PEBytes', '$DecodedPE', escape=None),
                         PSArg('ExeArgs', command.command_line))
    return powershell_function(rat, anchor, command)


#
# Agent Commands
#
def get_clients(host: Host) -> Job:
    return Job.create_agent_command(host, 'clients')


def write_commander(host: Host, path: str) -> Job:
    return Job.create_agent_command(host, "write_commander", path=path)


def agent_shell_command(host: Host, command_line: str) -> Job:
    return Job.create_agent_command(host, 'execute', command_line=command_line)


def create_process(host: Host, process_args: str, parent: Union[str, int]=None, hide: bool=True,
                   output: bool=False) -> Job:
    return Job.create_agent_command(host, 'create_process', process_args=process_args, parent=parent, hide=hide,
                                    output=output)


def create_process_as_user(host: Host, process_args: str, user_domain: str, user_name: str, user_pass: str,
                           parent: str=None, hide: bool=True, output: bool=False) -> Job:
    return Job.create_agent_command(host, 'create_process_as_user', process_args=process_args, user_domain=user_domain,
                                    user_name=user_name, user_pass=user_pass, parent=parent, hide=hide, output=output)


def create_process_as_active_user(host: Host, process_args: str, parent: Union[str, int]=None, hide: bool=True,
                                  output: bool=False) -> Job:
    return Job.create_agent_command(host, 'create_process_as_active_user', process_args=process_args, parent=parent,
                                    hide=hide, output=output)
