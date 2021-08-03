import json
import os
import re
import asyncio
import aioftp

from app.utility.base_world import BaseWorld


class Contact(BaseWorld):
    def __init__(self, services):
        self.name = 'ftp'
        self.description = 'Accept agent beacons through ftp'
        self.contact_svc = services.get('contact_svc')
        self.file_svc = services.get('file_svc')
        self.logger = BaseWorld.create_logger('contact_ftp')
        self.host = self.get_config('app.contact.ftp.host')
        self.port = self.get_config('app.contact.ftp.port')
        self.directory = self.get_config('app.contact.ftp.server.dir')
        self.user = self.get_config('app.contact.ftp.user')
        self.pword = self.get_config('app.contact.ftp.pword')
        self.home = os.getcwd()
        self.server = None

    async def start(self):
        self.set_up_server()
        t = asyncio.create_task(self.ftp_server())
        await t

    def set_up_server(self):
        # If directory doesn't exist, make the directory
        if not os.path.exists(self.directory):
            os.makedirs(self.directory)

        # Define a new user with full r/w permissions
        u = (
            aioftp.User(
                str(self.user),
                str(self.pword),
                home_path=str(self.directory),
                permissions=(
                    aioftp.Permission("/", readable=False, writable=False),
                    aioftp.Permission(str(self.directory), readable=True, writable=True),
                ),
                maximum_connections=256,
                read_speed_limit=1024 * 1024,
                write_speed_limit=1024 * 1024,
                read_speed_limit_per_connection=100 * 1024,
                write_speed_limit_per_connection=100 * 1024
            ),
            aioftp.User(
                home_path="/anon",
                permissions=(
                    aioftp.Permission("/", readable=False, writable=False),
                    aioftp.Permission("/anon", readable=True),
                ),
                maximum_connections=5,
                read_speed_limit=1024 * 1024,
                write_speed_limit=1024 * 1024,
                read_speed_limit_per_connection=100 * 1024,
                write_speed_limit_per_connection=100 * 1024
            ),
        )
        # Instantiate FTP server on local host and listen on 1026
        self.server = MyServer(u, self.contact_svc, self.file_svc, self.logger, self.host, self.port, self.user,
                               self.pword, self.directory, self.home)

    async def ftp_server(self):
        await self.server.run(host=self.host, port=self.port)


class MyServer(aioftp.Server):
    def __init__(self, u, contact, file, log, host_ip, port_in, user, password, u_dir, start,
                 *,  max_con=256):
        super().__init__(u, maximum_connections=max_con)
        self.contact_svc = contact
        self.file_svc = file
        self.logger = log
        self.host = host_ip
        self.port = port_in
        self.login = user
        self.pword = password
        self.directory = u_dir
        self.home = start

    @aioftp.ConnectionConditions(
        aioftp.ConnectionConditions.login_required,
        aioftp.ConnectionConditions.passive_server_started)
    @aioftp.PathPermissions(aioftp.PathPermissions.writable)
    async def stor(self, connection, rest, mode="wb"):

        @aioftp.ConnectionConditions(
            aioftp.ConnectionConditions.data_connection_made,
            wait=True,
            fail_code="425",
            fail_info="Can't open data connection")
        @aioftp.worker
        async def stor_worker(self, connection, rest):
            stream = connection.data_connection
            del connection.data_connection
            if connection.restart_offset:
                file_mode = "r+b"
            else:
                file_mode = mode
            file_out = connection.path_io.open(real_path, mode=file_mode)

            bytes_obj = b''
            file = False
            p_load = False

            async with file_out, stream:
                if connection.restart_offset:
                    await file_out.seek(connection.restart_offset)
                async for data in stream.iter_by_block(connection.block_size):
                    bytes_obj += data

            if re.match(r"^Alive\.txt$", name[len(name) - 1]):
                file = True
                profile = json.loads(bytes_obj.decode())
                paw, response = await r_class.create_response(profile)
                success = r_class.write_response_file(paw, response)
                if not success:
                    self.logger.debug("ERROR: Failed to create response")

            if re.match(r"^Payload\.txt$", name[len(name) - 1]):
                p_load = True
                profile = json.loads(bytes_obj.decode())
                file_path, contents, display_name = await r_class.get_payload_file(profile)
                if file_path is not None:
                    r_class.write_file(profile.get('paw'), profile.get('file'), str(contents))

            if not file and not p_load:
                paw = name[len(name) - 2]
                filename = name[len(name) - 1]
                await r_class.submit_uploaded_file(paw, filename, bytes_obj)

            connection.response("226", "data transfer done")
            del stream
            return True

        real_path, virtual_path = self.get_paths(connection, rest)
        name = str(virtual_path).split("/")
        self.logger.debug("File: " + str(name[len(name) - 1]) + " received")
        r_class = CalderaServer(self.contact_svc, self.file_svc, self.logger, self.home, self.directory)

        if await connection.path_io.is_dir(real_path.parent):
            coro = stor_worker(self, connection, rest)
            task = asyncio.create_task(coro)
            connection.extra_workers.add(task)
            code, info = "150", "data transfer started"
        else:
            code, info = "550", "path unreachable"
        connection.response(code, info)
        return True


class CalderaServer:
    def __init__(self, contact, file, log, h, d):
        self.contact_svc = contact
        self.file_svc = file
        self.logger = log
        self.home = h
        self.directory = d

    async def create_response(self, profile):
        paw = profile.get('paw')
        profile['paw'] = paw
        profile['contact'] = profile.get('contact', 'ftp')
        agent, instructions = await self.contact_svc.handle_heartbeat(**profile)
        response = dict(paw=agent.paw,
                        sleep=await agent.calculate_sleep(),
                        watchdog=agent.watchdog,
                        instructions=json.dumps([json.dumps(i.display) for i in instructions]))
        if agent.pending_contact != agent.contact:
            response['new_contact'] = agent.pending_contact
            self.logger.debug('Sending agent instructions to switch from C2 channel %s to %s'
                              % (agent.contact, agent.pending_contact))
        return paw, response

    def write_response_file(self, paw, response):
        filename = str(self.home + self.directory)
        try:
            if not os.path.exists(filename):
                os.makedirs(filename)

            filename += "/" + paw + "/Response.txt"
            with open(filename, "w+") as f:
                f.write(json.dumps(response))
            self.logger.debug("Beacon response created: " + filename)

        except IOError:
            self.logger.info("ERROR: Failed to create response file")
            return False, "", ""
        return True

    def write_file(self, paw, file_name, contents):
        filename = str(self.home + self.directory)
        try:
            if not os.path.exists(filename):
                os.makedirs(filename)

            filename += "/" + paw + "/" + file_name
            with open(filename, "w+") as f:
                f.write(contents)
            self.logger.debug("File created: " + filename)

        except IOError:
            self.logger.info("ERROR: Failed to create file")
            return False
        return True

    async def get_payload_file(self, payload_dict):
        return await self.file_svc.get_file(payload_dict)

    async def submit_uploaded_file(self, paw, filename, data):
        created_dir = os.path.normpath('/' + paw).lstrip('/')
        saveto_dir = await self.file_svc.create_exfil_sub_directory(dir_name=created_dir)
        await self.file_svc.save_file(filename, data, saveto_dir)
        self.logger.debug('Uploaded file: %s/%s' % (saveto_dir, filename))
