Platform: Kubernetes
====================

**Kubernetes Platform** abstracts your infrastructure into Kubernetes clusters. For environments that use
Kubernetes, Strong-OpX will deploy resources using kubectl (the command-line tool for interacting with
Kubernetes clusters). This platform is ideal for managing containerized applications and deployments within a
Kubernetes Cluster.

Kubernetes platform will be automatically selected if your environment configuration contains ``kubernetes`` key.

Configuration
-------------

Kubernetes platform configuration goes inside environment config under
``kubernetes`` namespace.

.. code:: yaml

   kubernetes:
     cluster_name:  # Required - EKS Cluster Name
     service_role:  # Optional - ARN of service Role. If specified all kubernetes operations will be
                    # executed using this service role

Deploying using ``kubectl``
---------------------------

For deploying Kubernetes artifacts, create a folder in your desired
repository called ``kubectl``. Put your YAMLs under that directory. When
you run

.. code:: shell

   strong-opx deploy --project <project-name> --env <env-name>

The directories’ contents will be scanned and each file deployed.

You can provide an alternate, relative path like so:

.. code:: shell

   strong-opx deploy --project <project-name> --env <env-name> kubectl/[someSubdirectory]

However, there are limitations to that path:

1. The path is relative to the root of the project. If your project is
   at ``/Users/jdoe/my-project/``, there must exist a
   ``/Users/jdoe/my-project/kubectl/[someSubdirectory]/`` when providing
   ``kubectl/[someSubdirectory]``.
2. You can only go one sub-directory “deep”. I.E. Providing a path of
   ``kubect/subdir/another-dir/`` will NOT have any YAML’s applied

Environment Specific Configurations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Sometimes you may want to deploy different things to different
environments. If that is the case, specify the environment you want to
run in the file name. For instance if you wanted to deploy ``foo`` to
only the staging environment you would name the file
``foo.staging.yml``. Then when you execute a deploy pointed to that
staging environment that file will be deployed. If you trigger a
production environment deployment, ``foo`` will not be deployed.

Updating ``kubeconfig``
-----------------------

``kubeconfig`` is cached and in case cluster is redeployed or for some
reasons ``kubeconfig`` needs to be updated, use below command to update
``kubeconfig``.

.. code:: shell

   strong-opx kubectl --update-kubeconfig -- version
