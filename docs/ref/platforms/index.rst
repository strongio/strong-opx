Platforms
=========

Each environment in Strong-OpX can utilize one or more Platforms to define where and how your infrastructure is
deployed. However, platforms do not need to be explicitly defined in your configuration. Based on the settings
specified in the `config.yml` file, Strong-OpX automatically determines the appropriate platform for the environment.

There are two main types of platforms supported:

.. toctree::
   :maxdepth: 1

   generic
   kubernetes

While you don’t need to manually define the platform in the configuration, Strong-OpX will intelligently pick the
correct platform based on the provided configuration details, enabling the appropriate deployment method to be used.
