=======================
Encoding External Files
=======================

CALDERA uses a simple encoding scheme to disguise some of the external
scripts and tools used by the project. This can be useful in preventing
AV software from interfering with the operation
of the CALDERA server.


Using the script editor
-----------------------

Small changes to external scripts can be made via the
CALDERA web application via the built-in Script Editor.

Manually with encode.py
-----------------------

For larger changes and encoding binary files ``scripts/encode.py`` can be
used.  This script will read in a file specified with the ``-i`` option
and output an encoded file to a path specified with the ``-o`` option.


Example
^^^^^^^

The following series of commands are an example of downloading and encoding
a new version of powerview using the ``encode.py`` script.

    .. code-block:: bash

        cd scripts/

        # Download a version of powerview from Empire's dev branch
        curl -L -o powerview.ps1 https://github.com/EmpireProject/Empire/raw/dev/data/module_source/situational_awareness/network/powerview.ps1

        # Encode the powershell script
        python encode.py -i powerview.ps1  -o powerview-ps1

        mv powervew-ps1 ../caldera/files

        # remove the downloaded file
        rm powerview.ps1