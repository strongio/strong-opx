Strong-OpX: Working with Project
================================

Scaffold Project
----------------

.. code:: shell

   strong-opx project create <project-name>

This will create a project inside a directory named ``<project-name>``.
This also registers the project in Strong-OpX global projects registry.

Register an Existing Project
----------------------------

If the project already exists, you can clone that repository to a local
path on your drive and register that instead of creating a new one:

.. code:: shell

   git clone git@github.com/strongio/<project-name>
   strong-opx project register ./<project-name>

Scaffold Environment
--------------------

An environment for many applications would be something like ``staging``
or ``production``. If you are just deploying a server for research, it
can just be something like ``default`` or ``main``.

To scaffold an environment, go to the project directory and use the
following command:

.. code:: shell

   strong-opx g environment
