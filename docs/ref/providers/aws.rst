AWS Provider
============

The AWS provider enables Strong-OpX to manage resources on Amazon Web Services. It supports all core features,
including compute instance management, Kubernetes cluster operations (with kubectl and Helm), container image
building (with auto-tagging), and variable/secret management.

Configuration
-------------
To configure the AWS provider, specify the configuration in your project config (`strong-opx.yml`).

.. code-block:: yaml

    aws:
      region: <region-name>    # Optional: AWS region (e.g., us-east-1)

Additionally AWS provider configuration can also be specified in an environment-specific config file
(`environments/<environment>/config.yml`). In that case the configuration from the environment file will override
the project-level configuration.

Secret Provider
---------------

Strong-OpX supports secret management via AWS SSM Parameter Store. To use this, configure the secret provider as
follows in your project config (`strong-opx.yml`):

.. code-block:: yaml

    secret:
      provider: aws_ssm           # Required: Name of secret provider. Only 'aws_ssm' is supported
      parameter: <name>           # Optional: AWS SSM Parameter Name. Supports templating, e.g. secret-{{ ENVIRONMENT }}
      secret_length: <int>        # Optional: Secret length (used when creating a new secret). Default is 24
