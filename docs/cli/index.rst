CLI Commands
============

Strong-OpX provides a wide range of commands to assist with managing your infrastructure and deployments.
These commands can be broadly divided into two categories:

Global
------

Global commands do not require any specific project or environment setup. These commands can be executed from
any directory, even outside a project structure. They are often used for tasks that are not tied to a particular
project, such as configuring AWS credentials or interacting with general system settings.

.. toctree::
   :maxdepth: 1

   aws-configure
   aws-ec2
   aws-mfa
   config
   project

Project Specific
----------------

These commands require a project and environment to be defined. When running project-specific commands if project or
environment isn't specified in arguments, Strong-OpX will intelligently determine the appropriate project and
environment based on the context, or prompt you to select them if necessary.

Project-specific commands require you to have a project and environment defined in order to execute them.
When running these commands, Strong-OpX will attempt to automatically determine the correct project and environment
based on the context. Here's how the selection process works:

1. **Project Selection**: Strong-OpX will attempt to find the closest `strong-opx.yml` configuration file in the
   current directory or any parent directory. If such a file is found, Strong-OpX will automatically select that
   project.

   If no `strong-opx.yml` is found, Strong-OpX will prompt you to select from the available known projects.

2. **Environment Selection**: After a project is selected, Strong-OpX will check if there is exactly one environment
   defined within the project. If only one environment exists, it will be automatically selected.

   If multiple environments are defined, Strong-OpX will prompt you to select the environment you want to use.


If Strong-OpX attempts to select a project or environment but encounters issues (such as an unregistered project
or missing configurations), it will raise an error with a helpful message explaining the issue and suggesting
corrective steps.


.. toctree::
   :maxdepth: 1

   deploy
   docker-build
   generate
   helm
   k8s
   kubectl
   packer
   playbook
   run
   scp
   ssh
   terraform
   vars


Getting Help
------------

To get detailed help for any command, simply append the `--help` flag to the command. This will display a
comprehensive breakdown of the command’s syntax, available options, and examples of how to use it.

For example, to get help with the `aws:ec2` command, you would run:

.. code-block:: bash

    strong-opx aws:ec2 --help

This will show you the available options and, where applicable, examples that demonstrate how to use the command
effectively.
