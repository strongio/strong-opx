Strong-OpX Introduction
=======================

This tool is designed to simplify and automate your deployment processes by bringing together powerful features
like infrastructure management, secure secret handling, and templating into a unified workflow. Strong-OpX's
flexibility allows you to manage your infrastructure with ease, whether you're working with EC2 instances or
Kubernetes clusters, while also securely handling variables and secrets across multiple environments.

To get started with Strong-OpX, it's important to understand a few core concepts that shape the way you interact
with the tool: **Project**, **Environment**, and **Platform**. These concepts form the foundation of how you organize
and manage your deployments.

Project
-------

The Project is the top-level entity in Strong-OpX. It represents the overarching structure that binds everything
together. Each project is unique and is represented by a directory in your file system. Inside this directory,
you will find the essential `strong-opx.yml` configuration file, which defines the project-specific settings.
Projects allow you to maintain a clear, organized structure for your deployments and ensure consistency across
environments.

.. seealso::
    - :doc:`./working-with-projects`

Environment
-----------

Within each project, you can define one or more Environments. An environment is a distinct configuration of
your deployment pipeline, typically representing different stages like development, staging, or production.
Each environment has its own directory located inside the `<project-root>/environments/` folder, where the specific
configuration of that environment is stored in the `config.yml` file. This allows you to easily manage different
configurations and settings for each environment within a project.

.. seealso::
    - :doc:`./ref/environment`

Platform
--------

Each environment in Strong-OpX can utilize one or more Platforms to define where and how your infrastructure is
deployed. However, platforms do not need to be explicitly defined in your configuration. Based on the settings
specified in the `config.yml` file, Strong-OpX automatically determines the appropriate platform for the environment.

There are two main types of platforms supported:

1. **Generic Platform** is used to manage EC2 instances directly. If your environment is set to use this
   platform, Strong-OpX will leverage Ansible playbooks for deployment. Ansible allows you to automate the setup,
   configuration, and management of EC2 instances, providing an efficient way to handle your infrastructure.

2. **Kubernetes Platform** abstracts your infrastructure into Kubernetes clusters. For environments that use
   Kubernetes, Strong-OpX will deploy resources using kubectl (the command-line tool for interacting with
   Kubernetes clusters). This platform is ideal for managing containerized applications and deployments within a
   Kubernetes environment.

While you don’t need to manually define the platform in the configuration, Strong-OpX will intelligently pick the
correct platform based on the provided configuration details, enabling the appropriate deployment method to be used.

.. seealso::
    - :doc:`./ref/platform-generic`
    - :doc:`./ref/platform-kubernetes`

With these concepts in place, you can use Strong-OpX to create, manage, and deploy your projects in a structured and
consistent way, while ensuring that all variables, secrets, and configurations are handled securely and efficiently.
Let's dive deeper into the features and capabilities of Strong-OpX as you explore how to leverage these concepts
for your deployments.
