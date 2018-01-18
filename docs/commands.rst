============
Commands API
============

The Commands API contains helper functions for constructing :py:class:`caldera.app.commands.command.CommandLine`
objects and parser functions to parse the output of those commands when run. It is typically used when creating
custom Steps.


CommandLine
-----------

.. autoclass:: caldera.app.commands.command.CommandLine
   :members: __init__


CommandLine generators
-----------------------

.. automodule:: caldera.app.commands.cmd
   :members:
.. automodule:: caldera.app.commands.footprint
   :members:
.. automodule:: caldera.app.commands.mimikatz
   :members:
.. automodule:: caldera.app.commands.nbtstat
   :members:
.. automodule:: caldera.app.commands.net
   :members:
.. automodule:: caldera.app.commands.powershell
   :members:
.. automodule:: caldera.app.commands.psexec
   :members:
.. automodule:: caldera.app.commands.reg
   :members:
.. automodule:: caldera.app.commands.sc
   :members:
.. automodule:: caldera.app.commands.schtasks
   :members:
.. automodule:: caldera.app.commands.systeminfo
   :members:
.. automodule:: caldera.app.commands.taskkill
   :members:
.. automodule:: caldera.app.commands.tasklist
   :members:
.. automodule:: caldera.app.commands.wmic
   :members:
.. automodule:: caldera.app.commands.xcopy
   :members:

Parser Exceptions
-----------------

.. automodule:: caldera.app.commands.errors
   :members:
