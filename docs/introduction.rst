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
    - :doc:`./working-with-terraform`

Platform
--------

A **Platform** defines the environment where your infrastructure is deployed and managed. Platforms serve as an
abstraction layer that allows you to interact with different types of infrastructure without needing to worry about
the underlying details. Platform configurations are specified within the `config.yml` file of each environment.

.. seealso::
    For details about platforms configurations and available platform, see the
    :doc:`ref/platforms/index` documentation.

Provider
--------

A **Provider** in Strong-OpX represents an integration with a cloud platform, such as AWS or Azure. Providers are
responsible for enabling Strong-OpX to manage resources and perform operations on these platforms. Each provider
exposes a set of features, such as compute instance management, Kubernetes and Helm operations, container image
building, and secret management. The specific features available depend on the provider.

One project can utilize only one provider. To choose a provider for your project, you need to specify it in the
project configuration file (`strong-opx.yml`).

Provider specific additional configuration can also be specified in an environment-specific configuration file
(`environments/<environment>/config.yml`). Strong-OpX will use the most specific configuration available for the
current environment.

.. seealso::
    For details on configuring each provider and their supported features, see the
    :doc:`ref/providers/index` documentation.

With these concepts in place, you can use Strong-OpX to create, manage, and deploy your projects in a structured and
consistent way, while ensuring that all variables, secrets, and configurations are handled securely and efficiently.
Let's dive deeper into the features and capabilities of Strong-OpX as you explore how to leverage these concepts
for your deployments.
