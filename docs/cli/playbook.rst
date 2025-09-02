``playbook``
============

.. autoprogram:: strong_opx.management.commands.playbook:Command().create_parser()
   :groups:
   :prog: strong-opx playbook


.. note::

    This command is a thin wrapper around ``ansible-playbook``. It will
    automatically set the inventory file based on the current environment.

    To pass additional arguments to ``ansible-playbook`` you can use the ``--`` separator.
    All arguments after ``--`` will be passed as it is to ``ansible-playbook``.
