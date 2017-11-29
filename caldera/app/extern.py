import os
import zipfile
import errno
import io
import shutil
from .util import grab_site


def load_psexec():
    target_file = '../dep/tools/ps.hex'
    pstools = grab_site('https://download.sysinternals.com/files/PSTools.zip', stream=True, params=None, mode='psexec')
    if not os.path.exists(os.path.dirname(target_file)):
        try:
            os.makedirs(os.path.dirname(target_file))
        except OSError as error:
            if error.errno != errno.EEXIST:
                raise
    unload_zip(pstools.content, 'PsExec.exe', target_file)


def unload_zip(zip_file, target_name: str, target_dest: str):
    with zipfile.ZipFile(io.BytesIO(zip_file)) as z:
        with z.open(target_name) as data:
            with open(target_dest, 'wb') as dest:
                shutil.copyfileobj(data, dest)
