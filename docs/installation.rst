Installing Strong-OpX
=====================

To get started with Strong-OpX, follow the steps below to install the tool and set it up for your project.
Strong-OpX requires **Python 3.9 or higher**, and it is recommended to install it in a separate virtual environment
for ease of use and isolation from other Python dependencies.

Install Python
--------------

Ensure that you have **Python 3.9** or higher installed on your system. You can check your Python version by running:

.. code:: shell

    python --version


If you don't have Python 3.9 or higher, please follow the instructions for installing the latest version of Python
from the official Python website: https://www.python.org/downloads/

Create a Virtual Environment
----------------------------

It is highly recommended to create a separate virtual environment to install Strong-OpX. This ensures that
Strong-OpX's dependencies do not interfere with other Python projects you may be working on.

To create a virtual environment, run the following commands:

.. code:: shell

    python -m venv strong-opx-venv

Once the virtual environment is created, activate it:

.. code:: shell

    source strong-opx-venv/bin/activate


Install Strong-OpX
------------------

With the virtual environment activated, you can now install Strong-OpX. You can either install from source or from
prebuilt wheel.


Installing from Wheel
~~~~~~~~~~~~~~~~~~~~~~

.. code:: shell

   pip install https://s3-us-west-2.amazonaws.com/strong-packages/strong_opx-<version>-<python-version>-<python-version>-<platform>.whl


- `<version>`: Specific Strong-OpX version to install. For latest, use `latest`.
- `python-version`: The Python version for which the wheel is built. Supported values are `py39`, `py310`, `py311`
  and `py312`.
- `<platform>`: The platform for which the wheel is built. Supported values are `manylinux2014_x86_64` and
  `macosx_10_9_x86_64` for Linux and MacOS respectively.


Installing from Source
~~~~~~~~~~~~~~~~~~~~~~~

.. code:: shell

  git clone git@github.com:strongio/strong-opx
  pip install -e ./strong-opx


Create an Alias for Easy Access
-------------------------------

To avoid typing the full path to the virtual environment every time, or to avoid needing to activate the virtual
environment manually each time, we recommend creating an alias in your shell profile.

First get the path to the Strong-OpX executable:

.. code:: shell

    which strong-opx


Next, open your `~/.profile` or relevant shell profile file and add the following line to create an alias:

.. code:: shell

    alias strong-opx=<path-you-get-from-above>


Now, you can run Strong-OpX directly from the command line without needing to activate the virtual environment
manually each time.
