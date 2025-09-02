``scp``
=======

.. autoprogram:: strong_opx.management.commands.ssh:Command().create_parser()
   :groups:
   :prog: strong-opx ssh


Examples
~~~~~~~~

To download a file from any server in your environment:

.. code:: shell

   strong-opx scp <remote_host_or_ip> @</path/to/remote/file> /path/to/local/dir

This will connect to the server and download the file located at
``/path/to/remote/file`` to the folder ``/path/to/local/dir``. Similarly
to upload file from local to server:

.. code:: shell

   strong-opx scp <remote_host_or_ip> /path/to/local/dir @</path/to/remote/file>


.. note::

    This command is a thin wrapper around ``scp``. To pass additional arguments to ``scp`` you can use the
    ``--`` separator. All arguments after ``--`` will be passed as it is to ``scp``.
