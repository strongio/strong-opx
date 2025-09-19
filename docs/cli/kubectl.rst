``kubectl``
===========

.. autoprogram:: strong_opx.management.commands.kubectl:Command().create_parser()
   :groups:
   :prog: strong-opx kubectl


.. note::

    All additional arguments passed to the kubectl command are passed directly to the kubectl command. This means
    that you can use any kubectl command and arguments that you would normally use with the kubectl command line tool.

    Additionally, any argument passed after the `--` separator will be passed directly to the kubectl command. This
    allows you to pass arguments that would otherwise be interpreted by the strong-opx kubectl command.


.. seealso::

    For more details on structuring kubernetes artifacts: :doc:`../ref/platforms/kubernetes`.
