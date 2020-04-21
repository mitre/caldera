import asyncio
import base64
import copy
import os
import subprocess

from aiohttp import web
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.service.interfaces.i_file_svc import FileServiceInterface
from app.utility.base_service import BaseService
from app.utility.payload_encoder import xor_file, xor_bytes

FILE_ENCRYPTION_FLAG = '%encrypted%'


class FileSvc(FileServiceInterface, BaseService):

    def __init__(self):
        self.log = self.add_service('file_svc', self)
        self.data_svc = self.get_service('data_svc')
        self.special_payloads = dict()
        self.encryptor = self._get_encryptor()
        self.encrypt_output = False if self.get_config('encrypt_files') is False else True

    async def get_file(self, headers):
        if 'file' not in headers:
            raise KeyError('File key was not provided')

        display_name = payload = headers.get('file')
        if any(payload.endswith(x) for x in [y for y in self.special_payloads if y.startswith('.')]):
            payload, display_name = await self._operate_extension(payload, headers)
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
        if file_path.endswith('.xored'):
            display_name = file_path.replace('.xored', '')
        return file_path, contents, display_name

    async def save_file(self, filename, payload, target_dir):
        self._save(os.path.join(target_dir, filename), payload)

    async def create_exfil_sub_directory(self, dir_name):
        path = os.path.join(self.get_config('exfil_dir'), dir_name)
        if not os.path.exists(path):
            os.makedirs(path)
        return path

    async def save_multipart_file_upload(self, request, target_dir):
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
        _, file_name = await self.find_file_path(name, location=location)
        if file_name:
            if file_name.endswith('.xored'):
                return name, xor_file(file_name)
            return name, self._read(file_name)
        raise FileNotFoundError

    def read_result_file(self, link_id, location='data/results'):
        buf = self._read(os.path.join(location, link_id))
        return buf.decode('utf-8')

    def write_result_file(self, link_id, output, location='data/results'):
        output = bytes(output, encoding='utf-8')
        self._save(os.path.join(location, link_id), output)

    async def add_special_payload(self, name, func):
        """
        Call a special function when specific payloads are downloaded

        :param name:
        :param func:
        :return:
        """
        if callable(func):  # Check to see if the passed function is already a callable function
            self.special_payloads[name] = func

    async def compile_go(self, platform, output, src_fle, arch='amd64', ldflags='-s -w', cflags='', buildmode='',
                         build_dir='.', loop=None):
        env = copy.copy(os.environ)
        env['GOARCH'] = arch
        env['GOOS'] = platform
        if cflags:
            for cflag in cflags.split(' '):
                name, value = cflag.split('=')
                env[name] = value

        args = ['go', 'build']
        if buildmode:
            args.append(buildmode)
        if ldflags:
            args.extend(['-ldflags', "{}".format(ldflags)])

        args.extend(['-o', output, src_fle])

        loop = loop if loop else asyncio.get_event_loop()
        try:
            await loop.run_in_executor(None, lambda: subprocess.check_output(args, cwd=build_dir, env=env))
        except subprocess.CalledProcessError as e:
            self.log.warning('Problem building golang executable {}: {} '.format(src_fle, e))

    def get_payload_name_from_uuid(self, payload):
        for t in ['standard_payloads', 'special_payloads']:
            for k, v in self.get_config(prop=t, name='payloads').items():
                if v['id'] == payload:
                    if v.get('obfuscation_name'):
                        return k, v['obfuscation_name'][0]
                    return k, k
        return payload, payload

    """ PRIVATE """

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

    def _get_encryptor(self):
        generated_key = PBKDF2HMAC(algorithm=hashes.SHA256(),
                                   length=32,
                                   salt=bytes(self.get_config('crypt_salt'), 'utf-8'),
                                   iterations=2 ** 20,
                                   backend=default_backend())
        return Fernet(base64.urlsafe_b64encode(generated_key.derive(bytes(self.get_config('encryption_key'), 'utf-8'))))

    async def _operate_extension(self, payload, headers):
        try:
            target = '.' + payload.split('.')[-1]
            return await self.special_payloads[target](self.get_services(), headers)
        except Exception as e:
            self.log.error('Error loading extension handler=%s, %s' % (payload, e))


def _go_vars(arch, platform):
    return '%s GOARCH=%s %s GOOS=%s' % (_get_header(), arch, _get_header(), platform)


def _get_header():
    return 'SET' if os.name == 'nt' else ''
