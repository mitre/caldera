import datetime
import os
import uuid

from app.utility.base_service import BaseService
from app.utility.payload_encoder import xor_file


class FileSvc(BaseService):

    def __init__(self, exfil_dir):
        self.exfil_dir = exfil_dir
        self.log = self.add_service('file_svc', self)
        self.data_svc = self.get_service('data_svc')
        self.special_payloads = dict()

    async def get_file(self, payload, platform=None):
        """
        Retrieve file
        :param filename: Request filename
        :param platform: Optional platform
        :return: File contents and optionally a display_name if the payload is a special payload
        """
        display_name = payload
        if payload in self.special_payloads:
            payload, display_name = await self.special_payloads[payload](dict(file=payload, platform=platform))
        file_path, contents = await self.read_file(payload)
        return file_path, contents, display_name

    async def upload_exfil(self, filename, payload):
        exfil_dir = await self._create_exfil_sub_directory(str(uuid.uuid4()))
        return await self.save_file(filename, payload, exfil_dir)

    async def save_file(self, filename, payload, target_dir):
        try:
            with open(os.path.join(target_dir, filename), 'wb') as f:
                f.write(payload)
            self.log.debug('Saved file %s' % filename)
            return True
        except Exception as e:
            self.log.debug('Exception uploading file %s' % e)
            return False

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

    async def _create_exfil_sub_directory(self, dir_name):
        dir_name = '{}.{}'.format(dir_name,
                                  datetime.datetime.now().strftime('%Y.%h.%d.%H.%M'))
        path = os.path.join(self.exfil_dir, dir_name)
        if not os.path.exists(path):
            os.makedirs(path)
        return path
