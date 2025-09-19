Azure Provider
=============

The Azure provider enables strong-opx to manage resources on Microsoft Azure. It currently supports only
variable/secret management via Azure Key Vault.

Configuration
-------------
To configure the AWS provider, specify the configuration in your project config (`strong-opx.yml`).

.. code-block:: yaml

    azure:
      subscription_id: <subscription-id>   # Optional: Azure Subscription ID
      resource_group: <resource-group>     # Optional: Azure Resource Group
      tenant_id: <tenant-id>               # Optional: Azure Tenant ID

Additionally Azure provider configuration can also be specified in an environment-specific config file
(`environments/<environment>/config.yml`). In that case the configuration from the environment file will override
the project-level configuration.

Secret Provider
---------------

strong-opx supports secret management via Azure Key Vault. To use this, configure the secret provider as follows in
your environment configuration:

.. code-block:: yaml

    secret:
      provider: keyvault              # Required: Name of secret provider. Only 'keyvault' is supported
      parameter: <name>               # Optional: Key Vault secret name. Supports templating, e.g. secret-{{ ENVIRONMENT }}
      secret_length: <int>            # Optional: Secret length (used when creating a new secret). Default is 24
      keyvault_url: <keyvault-url>    # Required: The URL of the Azure Key Vault instance
