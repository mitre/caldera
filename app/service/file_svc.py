import os
import uuid
import random
import string

from aiohttp import web
from shutil import which
from hashlib import md5

from app.service.base_service import BaseService


class FileSvc(BaseService):

    def __init__(self, plugins, exfil_dir):
        self.plugins = plugins
        self.exfil_dir = exfil_dir
        self.log = self.add_service('file_svc', self)
        self.data_svc = self.get_service('data_svc')

    async def download(self, request):
        """
        Accept a request with a required header, file, and an optional header, platform, and download the file
        :param request:
        :return: a multipart file via HTTP
        """
        name = await self._verify_file(request.headers.get('file'), request.headers.get('platform'))
        if name:
            _, file_path = await self.find_file_path(name, 'payloads')
            if file_path:
                headers = dict([('CONTENT-DISPOSITION', 'attachment; filename="%s"' % name)])
                return web.FileResponse(path=file_path, headers=headers)
        return web.HTTPNotFound(body='File not found')

    async def upload(self, request):
        """
        Accept a multipart file via HTTP and save it to the server
        :param request:
        :return: None
        """
        try:
            reader = await request.multipart()
            exfil_dir = await self._create_exfil_sub_directory(request.headers)
            while True:
                field = await reader.next()
                if not field:
                    break
                filename = field.filename
                with open(os.path.join(exfil_dir, filename), 'wb') as f:
                    while True:
                        chunk = await field.read_chunk()
                        if not chunk:
                            break
                        f.write(chunk)
                self.log.debug('Uploaded file %s' % filename)
            return web.Response()
        except Exception as e:
            self.log.debug('Exception uploading file %s' % e)

    async def find_file_path(self, name, location=''):
        """
        Find the location on disk of a file by name
        :param name:
        :param location:
        :return: a tuple: the plugin the file is found in & the relative file path
        """
        for plugin in self.plugins:
            for root, dirs, files in os.walk('plugins/%s/%s' % (plugin, location)):
                if name in files:
                    self.log.debug('Located %s' % name)
                    return plugin, os.path.join(root, name)

    """ PRIVATE """

    async def _create_exfil_sub_directory(self, headers):
        dir_name = headers.get('X-Request-ID', str(uuid.uuid4()))
        path = os.path.join(self.exfil_dir, dir_name)
        if not os.path.exists(path):
            os.makedirs(path)
        return path

    async def _compile(self, name, platform):

        if name.endswith('.go'):
            if which('go') is not None:
                plugin, file_path = await self.find_file_path(name)
                await self._change_file_hash(file_path)
                output = 'plugins/%s/payloads/%s-%s' % (plugin, name, platform)
                os.system('GOOS=%s go build -o %s -ldflags="-s -w" %s' % (platform.lower(), output, file_path))
                self.log.debug('%s compiled for %s with MD5=%s' %
                               (name, platform, md5(open(output, 'rb').read()).hexdigest()))
            return '%s-%s' % (name, platform)
        return name

    @staticmethod
    async def _change_file_hash(file_path, size=30):
        key = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(size))
        lines = open(file_path, 'r').readlines()
        lines[-1] = 'var key = "%s"' % key
        out = open(file_path, 'w')
        out.writelines(lines)
        out.close()
        return key

    async def _verify_file(self, name, platform):
        if not platform or not name:
            return
        valid_platforms = {ab['platform'].lower() for ab in await self.data_svc.explode_abilities()}
        if platform.lower() not in self.valid_platforms:
            return
        return await self._compile(name, platform.lower())