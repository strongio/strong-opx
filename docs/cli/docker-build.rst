``docker:build``
================

.. autoprogram:: strong_opx.management.commands.docker_build:Command().create_parser()
   :groups:
   :prog: strong-opx docker:build


.. seealso::

    - `docker build cli reference <https://docs.docker.com/engine/reference/commandline/build/>`__


All built images when pushed to ECR will be tagged with ``latest``, ``<environment>-latest`` alongside a generated
unique tag of format: ``<environment>-<revision>.<vcs-head-sha-hash>``. The ``<revision>`` is an auto-incrementing
number unique to the environment. ``<vcs-head-sha-hash>`` is the SHA-1 hash of the HEAD commit in the VCS repository
and will only be included in case of git repository.


.. note::

    If a project has two environments within the same AWS region and the ``--name`` value is the same for
    both environments, using ``latest`` tag can cause conflicts.

    For example, if a project had two environments, ``staging`` and ``development``, in the ``us-east-1``
    region of the same AWS account and the following commands were run:

    .. code:: shell

       strong-opx docker-build ./my-project --env=staging --push
       strong-opx docker-build ./my-project -env=development --push

    Both commands would push the newly-built Docker image to the same ``[AWS account]/my-project`` ECR repository
    overriding ``latest`` tag.

    To avoid this use ``<environment>-latest`` tag instead of ``latest`` tag.
