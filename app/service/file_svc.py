import asyncio.subprocess
import base64
import copy
import os

from aiohttp import web
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.utility.base_service import BaseService
from app.utility.payload_encoder import xor_file, xor_bytes

FILE_ENCRYPTION_FLAG = '%encrypted%'


class FileSvc(BaseService):

    def __init__(self):
        self.log = self.add_service('file_svc', self)
        self.data_svc = self.get_service('data_svc')
        self.special_payloads = dict()
        self.encryptor = self._get_encryptor()
        self.encrypt_output = False if self.get_config('encrypt_files') is False else True

    async def get_file(self, headers):
        """
        Retrieve file
        :param headers: headers dictionary. The `file` key is REQUIRED.
        :type headers: dict or dict-equivalent
        :return: File contents and optionally a display_name if the payload is a special payload
        :raises: KeyError if file key is not provided, FileNotFoundError if file cannot be found
        """
        if 'file' not in headers:
            raise KeyError('File key was not provided')

        display_name = payload = headers.get('file')
        if self.is_uuid4(payload):
            payload, display_name = self.get_payload_name_from_uuid(payload)
        if payload in self.special_payloads:
            payload, display_name = await self.special_payloads[payload](headers)
        file_path, contents = await self.read_file(payload)
        if headers.get('xor_key'):
            xor_key = headers['xor_key']
            contents = xor_bytes(contents, xor_key.encode())
        if headers.get('name'):
            display_name = headers.get('name')
        return file_path, contents, display_name

    async def save_file(self, filename, payload, target_dir):
        self._save(os.path.join(target_dir, filename), payload)

    async def create_exfil_sub_directory(self, dir_name):
        path = os.path.join(self.get_config('exfil_dir'), dir_name)
        if not os.path.exists(path):
            os.makedirs(path)
        return path

    async def save_multipart_file_upload(self, request, target_dir):
        """
        Accept a multipart file via HTTP and save it to the server

        :param request:
        :param target_dir: The path of the directory to save the uploaded file to.
        """
        try:
            reader = await request.multipart()
            while True:
                field = await reader.next()
                if not field:
                    break
                filename = field.filename
                await self.save_file(filename, bytes(await field.read()), target_dir)
                self.log.debug('Uploaded file %s/%s' % (target_dir, filename))
            return web.Response()
        except Exception as e:
            self.log.debug('Exception uploading file: %s' % e)

    async def find_file_path(self, name, location=''):
        """
        Find the location on disk of a file by name.

        :param name:
        :param location:
        :return: a tuple: the plugin the file is found in & the relative file path
        """
        for plugin in await self.data_svc.locate('plugins', match=dict(enabled=True)):
            for subd in ['', 'data']:
                file_path = await self.walk_file_path(os.path.join('plugins', plugin.name, subd, location), name)
                if file_path:
                    return plugin.name, file_path
        file_path = await self.walk_file_path(os.path.join('data'), name)
        if file_path:
            return None, file_path
        return None, await self.walk_file_path('%s' % location, name)

    async def read_file(self, name, location='payloads'):
        """
        Open a file and read the contents

        :param name:
        :param location:
        :return: a tuple (file_path, contents)
        """
        _, file_name = await self.find_file_path(name, location=location)
        if file_name:
            if file_name.endswith('.xored'):
                return name, xor_file(file_name)
            return name, self._read(file_name)
        raise FileNotFoundError

    def read_result_file(self, link_id, location='data/results'):
        """
        Read a result file. If file encryption is enabled, this method will return the plaintext
        content.

        :param link_id: The id of the link to return results from.
        :param location: The path to results directory.
        :return:
        """
        buf = self._read(os.path.join(location, link_id))
        return buf.decode('utf-8')

    def write_result_file(self, link_id, output, location='data/results'):
        """
        Writes the results of a link execution to disk. If file encryption is enabled,
        the results file will contain ciphertext.

        :param link_id: The link id of the result being written.
        :param output: The content of the link's output.
        :param location: The path to the results directory.
        :return:
        """
        output = bytes(output, encoding='utf-8')
        self._save(os.path.join(location, link_id), output)

    async def add_special_payload(self, name, func):
        """
        Call a special function when specific payloads are downloaded

        :param name:
        :param func:
        :return:
        """
        self.special_payloads[name] = func

    def _save(self, filename, content):
        if self.encryptor and self.encrypt_output:
            content = bytes(FILE_ENCRYPTION_FLAG, 'utf-8') + self.encryptor.encrypt(content)
        with open(filename, 'wb') as f:
            f.write(content)

    def _read(self, filename):
        with open(filename, 'rb') as f:
            buf = f.read()
        if self.encryptor and buf.startswith(bytes(FILE_ENCRYPTION_FLAG, encoding='utf-8')):
            buf = self.encryptor.decrypt(buf[len(FILE_ENCRYPTION_FLAG):])
        return buf

    async def compile_go(self, platform, output, src_fle, arch='amd64', ldflags='-s -w', cflags='', buildmode='',
                         build_dir='.'):
        """
        Dynamically compile a go file

        :param platform:
        :param output:
        :param src_fle:
        :param arch: Compile architecture selection (defaults to AMD64)
        :param ldflags: A string of ldflags to use when building the go executable
        :param cflags: A string of CFLAGS to pass to the go compiler
        :param buildmode: GO compiler buildmode flag
        :param build_dir: The path to build should take place in
        :return:
        """
        env = copy.copy(os.environ)
        env['GOARCH'] = arch
        env['PLATFORM'] = platform
        if cflags:
            for cflag in cflags.split(' '):
                name, value = cflag.split(':')
                env[name] = value

        build_mode_args = ['-buildmode', buildmode] if buildmode else []

        process = await asyncio.subprocess.create_subprocess_exec('go', 'build', *build_mode_args, '-o', output,
                                                                  '-ldflags', ldflags, src_fle,
                                                                  cwd=build_dir, env=env,
                                                                  stdout=asyncio.subprocess.PIPE,
                                                                  stderr=asyncio.subprocess.PIPE)
        command_output = await process.communicate()
        if process.returncode != 0:
            self.log.warning('Error while compiling {}: {}'.format(src_fle, command_output))

    def get_payload_name_from_uuid(self, payload):
        for t in ['standard_payloads', 'special_payloads']:
            for k, v in self.get_config(prop=t, name='payloads').items():
                if v['id'] == payload:
                    if v.get('obfuscation_name'):
                        return k, v['obfuscation_name'][0]
                    return k, k
        return payload, payload

    """ PRIVATE """

    def _get_encryptor(self):
        generated_key = PBKDF2HMAC(algorithm=hashes.SHA256(),
                                   length=32,
                                   salt=bytes(self.get_config('crypt_salt'), 'utf-8'),
                                   iterations=2 ** 20,
                                   backend=default_backend())
        return Fernet(base64.urlsafe_b64encode(generated_key.derive(bytes(self.get_config('encryption_key'), 'utf-8'))))


def _go_vars(arch, platform):
    return "%s GOARCH=%s %s GOOS=%s" % (_get_header(), arch, _get_header(), platform)


def _get_header():
    return "SET" if os.name == "nt" else ""
