Project
=======

Configuration
-------------

.. code:: yaml

   name: <project-name>       # Required - Project name. Shouldn't be changed after initialization
   aws: # Optional - AWS Configuration specific to environment
     region: <region-name>    # Optional: AWS region

   strong_opx: # Optional
     required_version:  # Optional: Strong-OpX version requirements. i.e. "<1.14", ">=1.2", "==1.2" etc
     templating_engine: <'basic', 'jinja2'> # Optional: templating engine to use, defaults to 'basic'

   secret: # Required - Secret used to encrypt/decrypt vars
     provider: <name>    # Required: Name of secret provider. Currently, only aws_ssm is supported
     parameter: <name>   # Required: AWS SSM Parameter Name. It supports template i.e. secret-${ENVIRONMENT} will resolve
                         # to secret-production in case of production environment
     secret_length: <int>  # Optional - Secret length (Only used when secret is created). Default is 24
     upsert: <bool>        # Optional - If specified, secret will be created if that is missing. Default to True

   vars: # Required - See below for details

Variable path can be specified in different ways:

-  As string or template string i.e.

.. code:: yaml

   vars: vars/${ENVIRONMENT}.yml

-  As dictionary where key is name of environment and value can be str
   or list of str:

.. code:: yaml

   vars:
     production: vars/some-vars.yml
     staging:
       - vars/some-other-vars.yml
       - vars/some-other-vars-for-${ENVIRONMENT}.yml
     development: vars/some-other-vars-for-${ENVIRONMENT}.yml

-  As list of str or dictionary

.. code:: yaml

   vars:
     - vars/common.yml
     - vars/${ENVIRONMENT}.yml
     - production: vars/sensitive.yml
       staging: vars/fake.yml
       development:
         - vars/fake.yml
         - vars/${ENVIRONMENT}.yml

If specified vars path is missing, a warning will be thrown.
