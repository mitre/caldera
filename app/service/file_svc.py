import os

import aiohttp_jinja2
from aiohttp import web

from app.utility.logger import Logger


class FileSvc:

    def __init__(self, file_stores):
        self.file_stores = file_stores
        self.log = Logger('file_svc')

    async def render(self, request):
        name = request.headers.get('file')
        group = request.rel_url.query.get('group')
        environment = request.app[aiohttp_jinja2.APP_KEY]
        url_root = '{scheme}://{host}'.format(scheme=request.scheme, host=request.host)
        headers = dict([('CONTENT-DISPOSITION', 'attachment; filename="%s"' % name)])
        rendered = await self._render(name, group, environment, url_root)
        if rendered:
            return web.HTTPOk(body=rendered, headers=headers)
        return web.HTTPNotFound(body=rendered)

    async def download(self, request):
        name = request.headers.get('file')
        file_path, headers = await self._download(name)
        if file_path:
            return web.FileResponse(path=file_path, headers=headers)
        return web.HTTPNotFound(body='File not found')

    async def upload(self, request):
        try:
            reader = await request.multipart()
            field = await reader.next()
            filename = field.filename
            size = 0
            with open(os.path.join('/tmp/', filename), 'wb') as f:
                while True:
                    chunk = await field.read_chunk()
                    if not chunk:
                        break
                    size += len(chunk)
                    f.write(chunk)
            self.log.debug('Uploaded file %s' % filename)
        except Exception as e:
            self.log.debug('Exception uploading file %s' % e)

    @staticmethod
    async def _render(name, group, environment, url_root):
        try:
            t = environment.get_template(name)
            return t.render(url_root=url_root, group=group)
        except Exception:
            return None

    async def _download(self, name):
        for store in self.file_stores:
            for root, dirs, files in os.walk(store):
                if name in files:
                    headers = dict([('CONTENT-DISPOSITION', 'attachment; filename="%s"' % name)])
                    return os.path.join(root, name), headers
        return None, None
