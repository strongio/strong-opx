``terraform``
=============

.. autoprogram:: strong_opx.management.commands.terraform:Command().create_parser()
   :groups:
   :prog: strong-opx terraform


.. note::

    This command is a thin wrapper around ``terraform``. To pass additional arguments to ``terraform`` you can use the
    ``--`` separator. All arguments after ``--`` will be passed as it is to ``terraform``.
