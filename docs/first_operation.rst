============================
Running Your First Operation
============================

This section will you show how to get your first operation up and running.
An operation is the basic unit of Adversary Emulation.

.. note:: If you haven't already done so, follow the instructions in the :doc:`installation` section before proceeding

If the **CALDERA** server isn't running, start it by navigating to the caldera/ directory and executing

.. code-block:: console

    python caldera.py

Then navigate to the **CALDERA** interface at `<https://localhost:8888>`_

The default user account is `admin` and the default password is `caldera`

If you've followed the :doc:`installation` instructions, you should have some agents connected, check this by going to
the `Debug > Connected Agents` tab. If no agents are connected, go back to the :doc:`installation` instructions to ensure
that the Agents have been properly installed.

Creating an Adversary
---------------------
To perform an Operation, **CALDERA** needs an Adversary to emulate.
In **CALDERA**, an Adversary represents a real adversary's tactics and techniques. When we create our operation
we will select an Adversary to use which will dictate what techniques **CALDERA** performs during the operation.

We will create a simple Adversary.

Click on `Threat > Create Adversary`. This will take you to the adversary creation page. Several fields exist for you
to configure.

Name
    This is the name that you would like to give to the adversary, for this example name it whatever you would like

Steps
    These are the atomic actions that the adversary is allowed to perform. Steps are the main way in which you can
    change the behavior of your adversary. Each step gives the adversary new abilities to perform. Steps have a name and
    additionally are listed with their ATT&CK ID and ATT&CK Tactics. A detailed listing of each step is available
    by going to `Threat > Configure Steps`. For this example, select the
    following steps from the list:

     - copy_file: [T1105, Lateral Movement]
     - get_creds: [T1003, Credential Access]
     - get_admin: [T1086, Execution | T1069 & T1087, Discovery]
     - get_computers: [T1086, Execution | T1018, Discovery]
     - get_domain: [T1016, Discovery]
     - net_use: [T1077, Lateral Movement]
     - remote_process(WMI): [T1047, Execution]

Artifact Lists
    Artifact lists allow you to customize the artifacts that your adversary leaves behind. These artifacts include things
    like file and service names. For now we will leave this field blank to use the default artifact list.

Exfil Method
    **CALDERA** supports exfiltration techniques. This field defines how the adversary will exfiltrate data.
     - raw_tcp - exfiltrate using a tcp based protocol
     - http - exfiltrate using an http protocol
     - https - exfiltrate using an https protocol

Exfil Address
    This is the IP address that **CALDERA** will exfiltrate data to. Leaving it set as `x.x.x.x` will automatically
    use **CALDERA**'s runtime IP address automatically. Leave this set to `x.x.x.x` for now.

Exfil Port
    This is the TCP port that **CALDERA** will exfiltrate to. Leave this set to its default.

After completing this, click "Submit". You can now see the newly created Adversary. If you made a mistake click the
small pencil icon in the top right to edit the adversary.

Creating a Network
------------------
Now we will create a network for the adversary to operate on. Networks are just collections of host. They are a simple
way for **CALDERA** to organize and group together computers.

Navigate to `Networks > Create Network`. You will be brought to the adversary creation page. There are
a few fields for you to configure.

Name
    You can name the network you are creating. For this example give the network any name you would like

Domain
    This will let you select the domain name of the computers that you would like to include in this exercise.
    Every computer in a Network must be from the same domain. For this example select whichever
    domain is available.

Hosts
    Once you have selected your Domain, the Hosts field will populate. As Agents register with the **CALDERA** server,
    they are added to this field. Select as many hosts as you would like to participate in this game.

Click "Submit" at the bottom of this page to create the Network.

Create an Operation
-------------------

Now that we have created both an Adversary and a Network, we can create our first operation.

Go to `Operations > Create Operation`.

This will take you to the Operation creation page, where there are a lot of values to customize. We will explain
them all but most of them are advanced and we won't need to configure them.

Name
    You can give the Operation a name so that you can remember it.

Adversary
    You must select an Adversary which will be the agressor in this Operation. Pick the adversary that you created
    earlier.

Network
    You must select a network for this Operation which will limit the scope of the operation to the hosts contained
    in the Network you choose. Select the Network you created earlier.

Starting Host
    This is the first host that the Operation will start on. Select from one of the options.

Start Method
    This option lets you configure how the initial RAT will be created. Because **CALDERA** assumes that a network
    has already been compromised, **CALDERA** begins with a RAT running on the starting host. This field lets you configure
    how that RAT is created.

     - Existing Rat - If a RAT is already connected to **CALDERA**, you can use it as the starting RAT. If you select
       this option, an additional field will appear called "Starting Rat" that will allow you to pick the RAT you
       would like to start with.
     - Wait For New Rat - If you would like to launch the RAT manually, you may select this option to have **CALDERA**
       wait for a Rat to connect
     - Bootstrap Rat - **CALDERA** can automatically start a RAT on the starting host for you. Select this option.

Start Path
    You may tell **CALDERA** where you would like the Rat's executable file to be placed. Leave this empty to use the
    default location.

Starting User
    The Rat can be started in several different user contexts. This field lets you select the
    user context you would like the Rat to start as.

     - System - This is the System account. Leave this option selected.
     - Active User - This will start the Rat as the user account of whoever is logged in. If you select this option
       you will see a field called "Parent Process" appear, which will let you enter a process to use as the parent
       for the rat
     - Logon User - This will let you enter a specific user account to use. If you select this option, two fields will
       appear for you to enter the user name and password of the account that you would like the Rat to run under.

Auto-Cleanup
    **CALDERA** has the ability to cleanup after itself at the end of an operation. With a few exceptions,
    every technique that **CALDERA** executes can be cleaned up. Checking this box will perform the
    cleanup automatically when **CALDERA** is finished with the operation. Unchecking this box with allow you to
    manually trigger cleanup after the operation is over.

Command Delay (ms) & Command Jitter (ms)
    **CALDERA** typically runs techniques very quickly. If you would like to introduce some variability in how
    quickly **CALDERA** operates, you can artificially slow it down by adding delay and jitter. Every time CALDERA
    tries to execute a command, delay and jitter are used to calculate a sleep function. The value for this sleep is
    defined by the expression:

    .. code-block:: console

        delay + random(-jitter, jitter)

    where the function `random` returns a random number
    between its first and second parameter. For now leave delay and jitter set to 0.

Clone Previous Operation
    At the bottom of the screen you can also see that there is an option to clone a previous operation. This lets you
    quickly copy the settings from a previous Operation.

Now that you have configured the Operation select, "Submit".

.. warning:: Creating an Operation will immediately start running it.

This will create and start the operation, and take you to the operation view.

Observing an Operation
----------------------

In the Operation view, you can view the progress that **CALDERA** has made working on an operation.

The operation's status is displayed at the top of the screen next to the Operation's name.

Below the status, colored bubbles indicate the number of hosts and credentials that have been compromised during this
operation.

The bubbles on the left indicate **CALDERA**'s progress in compromising the network. Each bubble represents a host
within the network. Bubbles start out gray. When **CALDERA** discovers a host, that host's bubble turns blue.
When **CALDERA** gets a Rat on a host, that host turns red.

On the right is a pane called "Operation Details". This has several tabs that let you explore the operation.

Steps
    The Steps tab shows all of the steps that have been executed. Clicking on a step will expand the step to show the
    exact commands that **CALDERA** executed.

Jobs
    The Jobs tab is used for debugging

Artifacts
    The Artifacts tab lists artifacts that **CALDERA** creates on the network. At the moment only files that **CALDERA**
    creates are listed here

Cleanup Log
    The cleanup log lists any errors that occurred during operation cleanup.

