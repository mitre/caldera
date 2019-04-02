===============================
Adding New Adversary Techniques
===============================

.. note:: This page is a WIP. This is an advance copy of the final version.

In **CALDERA** an adversary's smallest executable action is called a ``Step``.

**CALDERA** pieces individual ``Steps`` together to form a sequence of activity that represents an adversary.

New techniques can be added to **CALDERA** by adding a new ``Step`` to the
``caldera\caldera\app\operation\operation_steps.py`` file. 

In this tutorial we'll show how this works. First by explaining one of the already existing ``Steps``.
Then we'll walk though adding a new ``Step``.


Understanding Steps
-------------------

Lets take a look at a simple step:

.. literalinclude:: ../caldera/app/operation/operation_steps.py
   :pyobject: DirListCollection

This Step finds files that have "password" or "admin" in the name. When it's run from the System user account,
it collects from all user's home directories otherwise it collects from the current user's home directory.
Let's break down some of what is going on here.

A Step is a class that inherits from the parent class `Step`. The name of the Step is the Class name.

.. literalinclude:: ../caldera/app/operation/operation_steps.py
   :pyobject: DirListCollection
   :lines: 1

.. warning:: The class name should be selected carefully, because it is used to uniquely identify the Step. If any code
    within the step is updated (for example to fix a bug) the class name is used to find and update the old definition.
    If a class is renamed, it will be treated as a completely new `Step`. Meanwhile the old `Step` will be removed from
    the definition of existing adversaries. For example, if Step "A" is renamed to "B". It is effectively treated
    as deleting step "A" (which removes it from any adversaries that may have been using it) and creating a new
    Step "B".

The step can be documented with a multiline comment. This comment will appear in
the CALDERA web interface under the Step's detailed view. Typically it contains a brief description of the step
and any requirements that might be necessary for it to work.

.. literalinclude:: ../caldera/app/operation/operation_steps.py
   :pyobject: DirListCollection
   :lines: 2-8

The step can be tagged with `ATT&CK <https://attack.mitre.org/wiki/Main_Page>`_ tactics and techniques. 
This is represented as a list of tuples, where the first item in each tuple is the ATT&CK technique (stored as the ID) 
and the second entry is the ATT&CK Tactic. The list is saved in the `attack_mapping` class variable. In this case the DirListCollection Step is tagged with three ATT&CK techniques.

.. literalinclude:: ../caldera/app/operation/operation_steps.py
   :pyobject: DirListCollection
   :lines: 9

The :code:`display_name` class variable stores the displayable name of the `Step`, which is listed on the web interface.

.. literalinclude:: ../caldera/app/operation/operation_steps.py
   :pyobject: DirListCollection
   :lines: 10

The :code:`summary` class variable is a short, one sentence description of what the step does.

.. literalinclude:: ../caldera/app/operation/operation_steps.py
   :pyobject: DirListCollection
   :lines: 11

The `preconditions` class variable stores the Step's requirements for execution. 

.. literalinclude:: ../caldera/app/operation/operation_steps.py
   :pyobject: DirListCollection
   :lines: 13-14

The preconditions define the objects that must exist for the `Step` to be executable.  
Preconditions can be thought of as database queries, in that they define 
objects, and conditions on those objects, that the Step needs in order to run.

Preconditions are stored in a 
format that is easily machine readable (and not necessarily human readable) so we'll spend some time 
explaining what they mean. Preconditions are stored as a list of tuples. Each precondition is its own tuple.
In this case there are two preconditions (one on each line).
The first item in the tuple gives the precondition a name; it must be a string. 
The second item in the tuple is an expression that represents an object and any conditions on that object.

That's the formal definition, let's talk about this example. Here's the first precondition: 

.. code:: python

   ('rat', OPRat)

The first item is the name of this precondition: ``rat``. The second item
defines the precondition. In this case, it is a single object, :code:`OPRat`, which is a type that represents
a `Rat`. There are no other conditions on this precondition, meaning that any object of type :code:`OPRat` which is 
known to CALDERA will match against the precondition.

Here is the second precondition:

.. code:: python

   ('host', OPHost(OPVar("rat.host")))

The first item names the precondition: :code:`'host'`. The second item starts with :code:`OPHost`, specifying that this 
precondition refers to objects that are `Hosts`. The next part of the expression
denotes conditions on the :code:`OPHost`. :code:`OPVar` is a special keyword which matches to a previously defined 
precondition. The entire expression, :code:`OPVar("rat.host")`, matches to the `host` field of the previously defined
`rat` precondition. In plain terms, the precondition :code:`OPHost(OPVar("rat.host"))` matches to an of object of
type :code:`OPHost` that is the same object as the :code:`host` field of the :code:`rat` precondition.

In psuedocode this would look something like this:

.. code:: python

   OPHost host = rat.host

Now that you understand these preconditions, we're going to jump down a bit to a different line to show how they're used.

.. literalinclude:: ../caldera/app/operation/operation_steps.py
   :pyobject: DirListCollection
   :lines: 28

This defines the Step's :code:`action` function. The action function is called when CALDERA decides to
execute the Step. Notice the parameters :code:`rat` and :code:`host` these match the preconditions that 
are defined above (because they match the precondition's names). When the Step is called, objects that
match the :code:`rat` and :code:`host` preconditions will be passed into the :code:`action` function.

There are some other parameters to the action function, for the moment you can ignore these, (we'll get
to them soon).

Moving back to where we left off, the next line is:

.. literalinclude:: ../caldera/app/operation/operation_steps.py
   :pyobject: DirListCollection
   :lines: 16-17

The class variable :code:`postconditions` defines the effects of the Step. This is used by CALDERA to predict 
outcome of a Step, so it can build plans of potential Steps to execute. 

The structure is similiar to :code:`preconditions`. The postconditions are a list of tuples. The 
first item in a tuple is 
the name of the postcondition, in this case :code:`'file_g'`. The second item defines the object that 
will be created as a result of the Step. In this case it is an :code:`OPFile` with two properties 
(represented by the dictionary). Each key-value pair in the dictionary represents properties that will
be in the object. So the :code:`OPFile` will have a field :code:`use_case` with a value of :code:`'collect'` and 
a :code:`'host'` field with a value of :code:`OPVar("host")` which is refers to the object in the :code:`host` 
precondition.

The postcondition is used to create the object within the :code:`action` function:

.. literalinclude:: ../caldera/app/operation/operation_steps.py
   :pyobject: DirListCollection
   :lines: 28

Like preconditions, postconditions are passed as a parameter to the action function. 

The class variable :code:`significant_parameters` allows the user to specify which parameters to the
:code:`action` function are significant for tracking repeated actions. 

.. literalinclude:: ../caldera/app/operation/operation_steps.py
   :pyobject: DirListCollection
   :lines: 19

By default CALDERA will not re-run an action if all of the parameters are the same as an action that has previously
been executed.
However, this behavior can be overridden using the :code:`significant_parameters` class variable.
Here we set the significant_parameter as "host" because we want this Step to only be performed 
once per host. If we had left
the default behavior here, this Step would have been run for every :code:`host` and :code:`rat` pair. Because there
can be multiple :code:`rat`s running on a host, this step would have been run multiple times on the same host which
is not what we want.

The last class variable in this example is the :code:`postproperties` variable. 

.. literalinclude:: ../caldera/app/operation/operation_steps.py
   :pyobject: DirListCollection
   :lines: 21

The :code:`postproperties` is a list of the fields that will be set on postconditions that are defined in the :code:`postconditions` 
class variable. 

Every Step must have a :code:`description` function:

.. literalinclude:: ../caldera/app/operation/operation_steps.py
   :pyobject: DirListCollection
   :lines: 23-25

The :code:`description` function must return a string detailing what the step does, preferably with
any runtime preconditions filled in. 
The description will be displayed in the operation view when the step is executed during an operation. Note that 
in this example the parameter names: :code:`rat` and :code:`host` match the names of the preconditions. 
When CALDERA runs this step, it will pass in the objects that it resolves for each precondition into the 
appropriate parameter.

Finally we have reached the last part of the `Step`, the :code:`action` function. We have seen this multiple 
times already. Here it is in its entirety:

.. literalinclude:: ../caldera/app/operation/operation_steps.py
   :pyobject: DirListCollection
   :lines: 27-

The function always takes at least one parameter: :code:`operation`. This is an instance of the 
:code:`OperationWrapper` class. It lets the Step perform actions on the Rat, like execute command lines.

The rest of the parameters are the names of preconditions or postconditions that need to be referenced.

The :code:`action` function contains all the code for the Step to actually perform the action that
it needs to. To do this, it will read preconditions (passed in as parameters), execute commands using the
:code:`operation` object, or create objects in the database using the postconditions.

Several other class variables exist that aren't used in this Step:

- :code:`value` - Default: :code:`1` - This can be used to prioritize this step over others. Steps with a large value
  will be executed before others.

- :code:`preproperties` - Default: :code:`[]` - similar to :code:`postproperties`, this is a list of strings that define
  fields that must be defined on any preconditions.

- :code:`deterministic` - Default: :code:`False` - this changes how CALDERA tracks whether a Step is redundant. When
  this is set to :code:`True` CALDERA will ignore the :code:`significant_parameters` and will instead use the
  ``postconditions`` to determine whether the step is redundant. More specifically, if the postconditions indicate that
  the step will add something new, like create a RAT on a host that doesn't currently have a RAT, CALDERA will perform
  the Step, even if it has already done the exact step before. This
  is probably easiest to understand with an example; most Lateral Movement Steps are labeled as deterministic
  because this allows them to repeated if a defender interferes with CALDERA, for example, by killing a running RAT.
  In some cases, its not possible to represent the outcome of a techniques. For example, credential dumping
  techniques often don't know ahead of time what credentials will be discovered. In this case, the postconditions
  can't accurately represent that outcome of the Step, so the Step is not deterministic.


Adding a New Step
-----------------

Now that we've deconstructed a Step, we'll walk through creating a new one. Our new step will search the current
user's home folder for files with a specific extension (.pem) and print the contents of the file.

To start, we'll create a new Step, fill in the appropriate ATT&CK tags and give it a name and summary:

.. code-block:: python
   :emphasize-lines: 1-4

    class PEMCollection(Step):
        attack_mapping = [("T1005", "Collection"), ("T1083", "Discovery"), ('T1106', 'Execution')]
        display_name = "Get PEM"
        summary = "Get the contents of files with a .pem extension with a for loop and the dir command recursively"


Next we will define the preconditions. We'll start with just a simple requirement for a rat:

.. code-block:: python
   :emphasize-lines: 6

    class PEMCollection(Step):
        attack_mapping = [("T1005", "Collection"), ("T1083", "Discovery"), ('T1106', 'Execution')]
        display_name = "Get PEM"
        summary = "Get the contents of files with a .pem extension with a for loop and the dir command recursively"

        preconditions = [('rat', OPRat)]


Next we will define the postconditions, in this case, we will say that we have collected 
files as a result of running this step. We also can define that the files are on the rat's
computer. 

.. code-block:: python
   :emphasize-lines: 8-9

    class PEMCollection(Step):
        attack_mapping = [("T1005", "Collection"), ("T1083", "Discovery"), ('T1106', 'Execution')]
        display_name = "Get PEM"
        summary = "Get the contents of files with a .pem extension with a for loop and the dir command recursively"

        preconditions = [('rat', OPRat)]
    
        postconditions = [('file_g', OPFile({'use_case': 'collected',
                                             'host': OPVar("rat.host")}))]


We only want this to be run once per host, so we'd like to set the significant parameters to be
the host that the Step is being exceuted on, which is the Rat's host (that is, :code:`rat.host`),
however we need to have the host as a named precondition in order to do this, so we will also
have to modify our preconditions to create a new precondition to refer to the Rat's host.  



.. code-block:: python
   :emphasize-lines: 7, 12

    class PEMCollection(Step):
        attack_mapping = [("T1005", "Collection"), ("T1083", "Discovery"), ('T1106', 'Execution')]
        display_name = "Get PEM"
        summary = "Get the contents of files with a .pem extension with a for loop and the dir command recursively"

        preconditions = [('rat', OPRat),
                         ('host', OPHost(OPVar("rat.host")))]

        postconditions = [('file_g', OPFile({'use_case': 'collect',
                                             'host': OPVar("host")}))]

        significant_parameters = ['host']

Next we will write the :code:`description` function. We can refer to objects in the preconditions,
which makes the description more tailored to the exact action that is being run.

.. code-block:: python
   :emphasize-lines: 14-16

    class PEMCollection(Step):
        attack_mapping = [("T1005", "Collection"), ("T1083", "Discovery"), ('T1106', 'Execution')]
        display_name = "Get PEM"
        summary = "Get the contents of files with a .pem extension with a for loop and the dir command recursively"

        preconditions = [('rat', OPRat),
                         ('host', OPHost(OPVar("rat.host")))]

        postconditions = [('file_g', OPFile({'use_case': 'collect',
                                             'host': OPVar("host")}))]

        significant_parameters = ['host']

        @staticmethod
        def description(rat, host):
            return "Using cmd to recursively look for .pem files to collect on {}".format(host.hostname)

Now we will write the action function. We'll just write a stub for now.

.. code-block:: python
   :emphasize-lines: 18-20

    class PEMCollection(Step):
        attack_mapping = [("T1005", "Collection"), ("T1083", "Discovery"), ('T1106', 'Execution')]
        display_name = "Get PEM"
        summary = "Get the contents of files with a .pem extension with a for loop and the dir command recursively"

        preconditions = [('rat', OPRat),
                         ('host', OPHost(OPVar("rat.host")))]

        postconditions = [('file_g', OPFile({'use_case': 'collect',
                                             'host': OPVar("host")}))]

        significant_parameters = ['host']

        @staticmethod
        def description(rat, host):
            return "Using cmd to recursively look for .pem files to collect on {}".format(host.hostname)

        @staticmethod
        async def action(operation):
            return True

At a minimum the :code:`action` function takes a parameter for the operation and has to return a boolean
indicating whether the action succeeded or failed. Next we'll add parameters for our preconditions and 
postconditions (the keyword names must match the names of the preconditions and postconditions as 
defined in the class variables).

.. code-block:: python
   :emphasize-lines: 19

    class PEMCollection(Step):
        attack_mapping = [("T1005", "Collection"), ("T1083", "Discovery"), ('T1106', 'Execution')]
        display_name = "Get PEM"
        summary = "Get the contents of files with a .pem extension with a for loop and the dir command recursively"

        preconditions = [('rat', OPRat),
                         ('host', OPHost(OPVar("rat.host")))]

        postconditions = [('file_g', OPFile({'use_case': 'collect',
                                             'host': OPVar("host")}))]

        significant_parameters = ['host']

        @staticmethod
        def description(rat, host):
            return "Using cmd to recursively look for .pem files to collect on {}".format(host.hostname)

        @staticmethod
        async def action(operation, rat, host, file_g):
            return True

Now we'll actually add some logic to the :code:`action` function. The first thing 
we need to identify is the user account that the Rat is running under. This will determine 
the files that we will be able to access. The rat's user context is stored in the 
:code:`username` field of the rat. This is a string that is formatted in the typical Windows
way, as :code:`<windows domain>\<username>`, for example, :code:`caldera\administrator`
or :code:`nt authority\system`.
If we are operating as the system user, we will be able to access all files, so we can search
the entire ``C:\Users\`` folder. Otherwise we will parse out the username portion and use 
that as the sub-directory within the Users's folder. 

.. note:: In some cases, the user's home folder will not be ``C:\Users\<username>``. To be more robust we should
   actually be using the ``USERPROFILE`` environment variable. However the CALDERA RAT does not yet support environment
   variable replacement so we construct the home folder using the username instead.

We have one last thing to do. To ensure that the :code:`rat.username` property exists, we have
to define it as a preproperty, otherwise the rat object that is provided may not have the
:code:`username` field defined.

Here is the Step with all of these changes: 

.. code-block:: python
   :emphasize-lines: 14, 22-25

    class PEMCollection(Step):
        attack_mapping = [("T1005", "Collection"), ("T1083", "Discovery"), ('T1106', 'Execution')]
        display_name = "Get PEM"
        summary = "Get the contents of files with a .pem extension in the user's home directory"

        preconditions = [('rat', OPRat),
                         ('host', OPHost(OPVar("rat.host")))]

        postconditions = [('file_g', OPFile({'use_case': 'collect',
                                             'host': OPVar("host")}))]

        significant_parameters = ['host']

        preproperties = ["rat.username"]

        @staticmethod
        def description(rat, host):
            return "Using cmd to recursively look for .pem files to collect on {}".format(host.hostname)

        @staticmethod
        async def action(operation, rat, host, file_g):
            if "system" in rat.username:
                path = "C:\\Users\\*.pem"
            else:
                path = "C:\\Users\\{}\\*.pem".format(rat.username.split("\\")[1])

            return True

Next we will execute a Windows command to recursively search through the directory to discover files 
that match our ``path``. This can be done with the Windows built-in command ``dir``. 
CALDERA has some utilities that generate command lines for Windows commands, including
``dir``. These are located in :py:mod:`caldera.app.commands` and are documented in :doc:`commands`. The function we want
to call is :py:func:`caldera.app.commands.cmd.dir_list`. The documentation shows that the command takes in a bunch of
arguments and returns two values,
an instance of :py:class:`caldera.app.commands.command.CommandLine` and a function that can 
parse the output of the ``dir`` command. This parser function will to the output of the ``dir`` command and
return to us a well formatted list of the files that were found.
We will pass both the CommandLine and the parser into the ``operation.execute_shell_command()``
function. ``operation`` is an instance of :py:class:`caldera.app.operation.operation_obj.OperationWrapper`.
The ``execute_shell_command()`` function takes a rat, a CommandLine and a parser function as arguments.
It will execute the CommandLine on the Rat and pass the output of the command to the parser,
returning the result of the parser which in this case will be a list of files ending with the 
`.pem` extension. The parser can also detect error outputs from ``dir``. We will catch the 
``FileNotFoundError``.

.. code-block:: python
   :emphasize-lines: 29-34

    from ..commands import cmd

    class PEMCollection(Step):
        attack_mapping = [("T1005", "Collection"), ("T1083", "Discovery"), ('T1106', 'Execution')]
        display_name = "Get PEM"
        summary = "Get the contents of files with a .pem extension in the user's home directory"

        preconditions = [('rat', OPRat),
                         ('host', OPHost(OPVar("rat.host")))]

        postconditions = [('file_g', OPFile({'use_case': 'collect',
                                             'host': OPVar("host")}))]

        significant_parameters = ['host']

        preproperties = ["rat.username"]

        @staticmethod
        def description(rat, host):
            return "Using cmd to recursively look for .pem files to collect on {}".format(host.hostname)

        @staticmethod
        async def action(operation, rat, host, file_g):
            if "system" in rat.username:
                path = "C:\\Users\\*.pem"
            else:
                path = "C:\\Users\\{}\\*.pem".format(rat.username.split("\\")[1])

            try:
                files = await operation.execute_shell_command(rat, *cmd.dir_list(search=path,
                                                                              b=True, s=True, a="-d"))
            except FileNotFoundError:
                # the path was invalid, the file wasn't found, or access denied, so move on
                pass

            return True

For each file that we discover with ``dir`` we want to print out the contents. One way of doing this is with the Windows
command ``type``. If we look at the :doc:`commands`, we can see that CALDERA does not have a generator
for the ``type`` command yet, so we'll make one.

The format is fairly straightforward:

.. code-block:: python

    # add this to the caldera.app.commands.cmd module
    def type(path: str) -> Tuple[CommandLine, Callable[[str], None]]:
        """
        type is the command to show the contents of the file

        Args:
            path: the path of the file contents to be shown
        """
        args = ['cmd /c type', "\"" + path + "\""]

        return CommandLine(args), parsers.cmd.type

Note that we are placing this function within the :mod:`caldera.app.commands.cmd` module because ``type`` is actually a
built in command to the Windows terminal program, cmd.exe. By convention, individual programs are stored in their
own module and sub-commands are stored within that module. However, you're free to follow whatever standard you would
like.

We'll also need a parser to parse the output of ``type``. In this case we don't actually have to do any special, so
our parser will rather simply just return everything.

.. code-block:: python

   # add this to the cmd class in caldera.app.commands.parsers
   @staticmethod
   def type(text: str) -> None:
       return text

.. note::  Parsers can be significantly more complex than the one that we have created here. One of the things they
   can do is raise exceptions when they encounter an error. Many different kinds of exceptions already exist
   and are documented in :mod:`caldera.app.commands.errors`. If you write a step that calls a command, be sure to
   check for any exceptions that may be generated. Feel free to add your own exceptions as well.

We can now call this from within the ``action`` function. Here's the completed code:

.. code-block:: python
   :emphasize-lines: 32-34

    from ..commands import cmd

    class PEMCollection(Step):
        attack_mapping = [("T1005", "Collection"), ("T1083", "Discovery"), ('T1106', 'Execution')]
        display_name = "Get PEM"
        summary = "Get the contents of files with a .pem extension in the user's home directory"

        preconditions = [('rat', OPRat),
                         ('host', OPHost(OPVar("rat.host")))]

        postconditions = [('file_g', OPFile({'use_case': 'collect',
                                             'host': OPVar("host")}))]

        significant_parameters = ['host']

        preproperties = ["rat.username"]

        @staticmethod
        def description(rat, host):
            return "Using cmd to recursively look for .pem files to collect on {}".format(host.hostname)

        @staticmethod
        async def action(operation, rat, host, file_g):
            if "system" in rat.username:
                path = "C:\\Users\\*.pem"
            else:
                path = "C:\\Users\\{}\\*.pem".format(rat.username.split("\\")[1])

            try:
                files = await operation.execute_shell_command(rat, *cmd.dir_list(search=path,
                                                                              b=True, s=True, a="-d"))
                for file in files:
                    contents = await operation.execute_shell_command(rat, *cmd.type(file))
                    print(contents)
            except FileNotFoundError:
                # the path was invalid, the file wasn't found, or access denied, so move on
                pass

            return True
