``ssh``
=======

.. autoprogram:: strong_opx.management.commands.ssh:Command().create_parser()
   :groups:
   :prog: strong-opx ssh


Examples
~~~~~~~~

If you know the private IP:

.. code:: shell

   strong-opx ssh <private-ip>

Otherwise, if you don’t know the private IP and you can specify host group.

.. code:: shell

   strong-opx ssh primary

Or if host group has multiple hosts, and you want to connect to non-zero host, you can specify index of host in host
config.

.. code:: shell

   strong-opx ssh <group-name>:<index>


.. note::

    This command is a thin wrapper around ``ssh``. To pass additional arguments to ``ssh`` you can use the
    ``--`` separator. All arguments after ``--`` will be passed as it is to ``ssh``.
