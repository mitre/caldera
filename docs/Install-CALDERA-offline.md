Install CALDERA offline
===================

To install CALDERA on a server without internet access, `pip` can be used to download the CALDERA dependencies
from a machine with internet access.  Once the dependencies are downloaded, they can be copied to the
offline machine and installed.

The internet machine's platform and python version should match offline server.  For example, if the 
the offline target machine runs Python 3.6 on CentOS 7, then Python3.6 and CentOS 7 should be used to perform 
the packaging to minimize problems.

```bash
git clone --recursive https://github.com/mitre/caldera.git
mkdir caldera/python_deps
pip download -r caldera/requirements.txt --dest caldera/python_deps
```

The `caldera` directory can now be copied to the offline server via whatever means are convenient (`scp` 
if there's connectivity, sneakernet, etc)

Once the `caldera` directory has been copied to the offline machine the dependencies can be installed with
pip.

```bash
pip install -r caldera/requirements.txt --no-index --find-links caldera/python_deps
```

CALDERA can then be started as usual:

```bash
cd caldera
python server.py
```