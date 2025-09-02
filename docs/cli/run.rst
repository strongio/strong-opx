``run``
=======

.. autoprogram:: strong_opx.management.commands.run:Command().create_parser()
   :groups:
   :prog: strong-opx run


.. note::

    The ``run`` command is used to run a command on a remote server. The command is executed in a new shell on
    the remote server and the output is streamed back to the local terminal. The command is executed as the
    user that the SSH connection is made with. The command is executed in the directory that the SSH connection
    is made to.

    All the arguments after ``--`` are passed as arguments to the command.
