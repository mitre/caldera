import csv
import os
import uuid

from aiohttp import web
from app.utility.logger import Logger


class FileSvc:

    def __init__(self, payload_dirs, exfil_dir):
        self.payload_dirs = [p for p in payload_dirs if os.path.isdir(p)]
        self.log = Logger('file_svc')
        self.exfil_dir = exfil_dir
        self.log.debug('Downloaded files will come from %s' % self.payload_dirs)

    async def download(self, request):
        name = request.headers.get('file')
        file_path, headers = await self.find_file(name)
        if file_path:
            return web.FileResponse(path=file_path, headers=headers)
        return web.HTTPNotFound(body='File not found')

    async def find_file(self, name):
        for store in self.payload_dirs:
            for root, dirs, files in os.walk(store):
                if name in files:
                    headers = dict([('CONTENT-DISPOSITION', 'attachment; filename="%s"' % name)])
                    self.log.debug('downloading %s...' % name)
                    return os.path.join(root, name), headers
        return None, None

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

    @staticmethod
    async def write_csv(dictionary, location):
        with open(location, 'w') as csv_file:
            fieldnames = dictionary[0].keys()
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            for element in dictionary:
                writer.writerow(element)

    """ PRIVATE """
            
    async def _create_unique_exfil_sub_directory(self):
        dir_name = str(uuid.uuid4())
        path = os.path.join(self.exfil_dir, dir_name)
        os.makedirs(path)
        return path
