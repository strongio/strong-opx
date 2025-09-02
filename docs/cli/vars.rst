``vars``
========

.. autoprogram:: strong_opx.management.commands.vars:Command().create_parser()
   :groups:
   :prog: strong-opx vars


Example
~~~~~~~

To encrypt variables defined inside project vars:

.. code:: shell

   strong-opx vars encrypt --vars <VARIABLE-1> [<VARIABLE-2> ...]

This will print the encrypted values and needs to be replacing manually in respective variable file.
An alternative is to encrypt variable value directly.

.. code:: shell

   strong-opx vars encrypt --value <value-to-encrypt>
