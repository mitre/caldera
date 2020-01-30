import os
import base64

from aiohttp import web
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

from app.utility.base_service import BaseService
from app.utility.payload_encoder import xor_file


FILE_ENCRYPTION_FLAG = '%encrypted%'


class FileSvc(BaseService):

    def __init__(self, exfil_dir, file_encryption=True, api_key=None, crypt_salt=None):
        self.exfil_dir = exfil_dir
        self.log = self.add_service('file_svc', self)
        self.data_svc = self.get_service('data_svc')
        self.special_payloads = dict()
        self.encryptor = self._get_encryptor(api_key, crypt_salt) if file_encryption else None

    async def get_file(self, request):
        """
        Retrieve file
        :param request: Request dictionary. The `file` key is REQUIRED.
        :type request: dict or dict-equivalent
        :return: File contents and optionally a display_name if the payload is a special payload
        :raises: KeyError if file key is not provided, FileNotFoundError if file cannot be found
        """
        if 'file' not in request:
            raise KeyError('File key was not provided')

        display_name = payload = request.get('file')
        if payload in self.special_payloads:
            payload, display_name = await self.special_payloads[payload](request)
        file_path, contents = await self.read_file(payload)
        if request.get('name'):
            display_name = request.get('name')
        return file_path, contents, display_name

    async def save_file(self, filename, payload, target_dir):
        with open(os.path.join(target_dir, filename), 'wb') as f:
            f.write(payload)
        self.log.debug('Saved file %s' % filename)

    async def create_exfil_sub_directory(self, dir_name):
        path = os.path.join(self.exfil_dir, dir_name)
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
                await self.save_file(filename, await field.read(), target_dir)
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
                file_path = await self._walk_file_path(os.path.join('plugins', plugin.name, subd, location), name)
                if file_path:
                    return plugin.name, file_path
        file_path = await self._walk_file_path(os.path.join('data'), name)
        if file_path:
            return None, file_path
        return None, await self._walk_file_path('%s' % location, name)

    async def read_file(self, name, location='payloads'):
        """
        Open a file and read the contents

        :param name:
        :param location:
        :return: a tuple (file_path, contents)
        """
        _, file_name = await self.find_file_path(name, location=location)
        if file_name:
            with open(file_name, 'rb') as file_stream:
                if file_name.endswith('.xored'):
                    return name, xor_file(file_name)
                return name, file_stream.read()
        raise FileNotFoundError

    def read_result_file(self, link_id, location='data/results'):
        """
        Read a result file. If file encryption is enabled, this method will return the plaintext
        content.

        :param link_id: The id of the link to return results from.
        :param location: The path to results directory.
        :return:
        """
        with open('%s/%s' % (location, link_id), 'rb') as fle:
            buf = fle.read()
        if self.encryptor and buf.startswith(bytes(FILE_ENCRYPTION_FLAG, encoding='utf-8')):
            buf = self.encryptor.decrypt(buf[len(FILE_ENCRYPTION_FLAG):])
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
        if self.encryptor:
            output = bytes(FILE_ENCRYPTION_FLAG, 'utf-8') + self.encryptor.encrypt(bytes(output, encoding='utf-8'))
        with open('%s/%s' % (location, link_id), 'wb') as fle:
            fle.write(output)

    async def add_special_payload(self, name, func):
        """
        Call a special function when specific payloads are downloaded

        :param name:
        :param func:
        :return:
        """
        self.special_payloads[name] = func

    @staticmethod
    async def compile_go(platform, output, src_fle, arch='amd64', ldflags='-s -w', cflags='', buildmode=''):
        """
        Dynamically compile a go file

        :param platform:
        :param output:
        :param src_fle:
        :param arch: Compile architecture selection (defaults to AMD64)
        :param ldflags: A string of ldflags to use when building the go executable
        :param cflags: A string of CFLAGS to pass to the go compiler
        :param buildmode: GO compiler buildmode flag
        :return:
        """
        os.system(
            'GOARCH=%s GOOS=%s %s go build %s -o %s -ldflags=\'%s\' %s' % (arch, platform, cflags, buildmode, output,
                                                                           ldflags, src_fle)
        )

    """ PRIVATE """

    @staticmethod
    async def _walk_file_path(path, target):
        for root, dirs, files in os.walk(path):
            if target in files:
                return os.path.join(root, target)
            if '%s.xored' % target in files:
                return os.path.join(root, '%s.xored' % target)
        return None

    def _get_encryptor(self, api_key, crypt_salt):
        if not (api_key and crypt_salt):
            self.log.error('File encryption requires setting api_key and crypt_salt in the config file.')
            return None

        generated_key = PBKDF2HMAC(algorithm=hashes.SHA256(),
                                   length=32,
                                   salt=bytes(crypt_salt, 'utf-8'),
                                   iterations=2 ** 20,
                                   backend=default_backend())
        return Fernet(base64.urlsafe_b64encode(generated_key.derive(bytes(api_key, 'utf-8'))))
