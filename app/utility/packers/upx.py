import os
import asyncio

name = 'upx'


class Packer:
    def __init__(self, file_svc):
        self.file_svc = file_svc
        self.packer_folder = 'data/payloads'

    async def pack(self, filename, contents):
        packed_file = os.path.join(self.packer_folder, filename)
        err = ''
        try:
            with open(packed_file, 'wb') as f:
                f.write(contents)
            command = 'upx %s' % filename
            process = await asyncio.create_subprocess_exec(*command.split(' '), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=self.packer_folder)
            _, stderr = await process.communicate()
            err = stderr.decode('utf-8')
            if not process.returncode:
                with open(packed_file, 'rb') as f:
                    buf = f.read()
                self.file_svc.log.debug('packed %s with %s packer' % (filename, name))
                return filename, buf
        except Exception as e:
            err = 'exception encountered when scanning, %s' % repr(e)
        finally:
            if os.path.exists(packed_file):
                os.remove(packed_file)

        raise Exception("Error encountered when packing %s with %s packer\nerror: %s" % (filename, name, err))
