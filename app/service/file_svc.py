import os
import uuid
import random
import string

from aiohttp import web
from shutil import which

from app.utility.logger import Logger


class FileSvc:

    def __init__(self, plugins, exfil_dir):
        self.plugins = plugins
        self.log = Logger('file_svc')
        self.exfil_dir = exfil_dir

    async def download(self, request):
        name = await self._compile(request.headers.get('file'), request.headers.get('platform'))
        _, file_path = await self._find_file_path(name, 'payloads')
        if file_path:
            headers = dict([('CONTENT-DISPOSITION', 'attachment; filename="%s"' % name)])
            return web.FileResponse(path=file_path, headers=headers)
        return web.HTTPNotFound(body='File not found')

    async def upload(self, request):
        try:
            reader = await request.multipart()
            exfil_dir = await self._create_unique_exfil_sub_directory()
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

    """ PRIVATE """

    async def _create_unique_exfil_sub_directory(self):
        dir_name = str(uuid.uuid4())
        path = os.path.join(self.exfil_dir, dir_name)
        os.makedirs(path)
        return path

    async def _compile(self, name, platform):
        if name.endswith('.go'):
            if which('go') is not None:
                plugin, file_path = await self._find_file_path(name)
                key = await self._insert_unique_deployment_key(file_path)
                self.log.debug('%s compiled for %s with key = %s' % (name, platform, key))
                output = 'plugins/%s/payloads/%s-%s' % (plugin, name, platform)
                os.system('GOOS=%s go build -o %s -ldflags="-s -w" %s' % (platform, output, file_path))
            return '%s-%s' % (name, platform)
        return name

    @staticmethod
    async def _insert_unique_deployment_key(file_path, size=30):
        key = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(size))
        lines = open(file_path, 'r').readlines()
        lines[-1] = 'var key = "%s"' % key
        out = open(file_path, 'w')
        out.writelines(lines)
        out.close()
        return key

    async def _find_file_path(self, name, location=''):
        for plugin in self.plugins:
            for root, dirs, files in os.walk('plugins/%s/%s' % (plugin, location)):
                if name in files:
                    self.log.debug('Located %s' % name)
                    return plugin, os.path.join(root, name)
