``helm``
========

.. autoprogram:: strong_opx.management.commands.helm:Command().create_parser()
   :groups:
   :prog: strong-opx helm


.. seealso::

    - `the Helm docs <https://helm.sh/docs/>`__
    - :doc:`../ref/helm`


.. caution::

    ``apply`` command does not support additional arguments and will be silently ignored.


.. caution::

    To run any helm command, specify that after the ``--`` separator. For example, to run ``helm list``,
    you would run ``strong-opx helm -- list``. This is because the ``strong-opx`` command has its own
    subcommands and options that are separate from the Helm command.
