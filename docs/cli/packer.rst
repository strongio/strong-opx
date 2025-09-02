``packer``
==========

.. autoprogram:: strong_opx.management.commands.packer:Command().create_parser()
   :groups:
   :prog: strong-opx packer


.. note::

    This command is a thin wrapper around the `Packer CLI
    <https://developer.hashicorp.com/packer/docs/commands>`__. It is intended to be used in the same way as the
    Packer CLI.

.. note::

    All additional arguments are passed directly to the Packer CLI. For example, to pass the ``-debug`` flag to
    Packer, you would run ``strong-opx packer -debug``.
