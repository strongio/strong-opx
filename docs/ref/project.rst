Project
=======

Configuration
-------------

.. code:: yaml

   name: <project-name>       # Required - Project name. Shouldn't be changed after initialization

   strong_opx: # Optional
     required_version:  # Optional: Strong-OpX version requirements. i.e. "<1.14", ">=1.2", "==1.2" etc
     templating_engine: <'basic', 'jinja2'> # Optional: templating engine to use, defaults to 'basic'

   secret: # Required - Look at provider specific documentation for details
   vars: # Required - See below for details

Provider specific configuration
-------------------------------

Look at provider specific documentation for details

`vars`
-----

Variable path can be specified in different ways:

-  As string or template string i.e.

.. code:: yaml

   vars: vars/{{ ENVIRONMENT }}.yml

-  As dictionary where key is name of environment and value can be str
   or list of str:

.. code:: yaml

   vars:
     production: vars/some-vars.yml
     staging:
       - vars/some-other-vars.yml
       - vars/some-other-vars-for-{{ ENVIRONMENT }}.yml
     development: vars/some-other-vars-for-{{ ENVIRONMENT }}.yml

-  As list of str or dictionary

.. code:: yaml

   vars:
     - vars/common.yml
     - vars/{{ ENVIRONMENT }}.yml
     - production: vars/sensitive.yml
       staging: vars/fake.yml
       development:
         - vars/fake.yml
         - vars/{{ ENVIRONMENT }}.yml

If specified vars path is missing, a warning will be thrown.
