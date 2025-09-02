Kubernetes Dashboard
====================

To install Kubernetes dashboard:

.. code:: shell

   strong-opx k8s --project <project> --env <env> dashboard install 

Connect Dashboard Proxy
-----------------------

.. code:: shell

   strong-opx k8s --project <project> --env <env> dashboard up [--no-browser] [-d / --detached]

Options:
~~~~~~~~

-  **``--no-browser`` (Optional):** Don’t automatically open browser
   **``--detach`` (Optional):** Start proxy in detached mode. To stop
   proxy use ``down`` command.

Stop Dashboard Proxy
--------------------

.. code:: shell

   strong-opx k8s --project <project> --env <env> dashboard down

Get Dashboard Token
-------------------

.. code:: shell

   strong-opx k8s --project <project> --env <env> dashboard token
