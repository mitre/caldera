import subprocess
from os import chdir
from os.path import join


chdir("caldera")
cmd = ["pyinstaller", 
       "caldera.py", 
       "--hidden-import=_cffi_backend", 
       "--distpath=" + join("..", "dist"), 
       "--workpath=" + join("..", "build"), 
       "--noconfirm",
       "--add-data=files;files",
       "--add-data=conf;conf"]
subprocess.run(cmd)
