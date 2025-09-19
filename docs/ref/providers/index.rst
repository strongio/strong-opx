Providers
=========

Provider represents an integration with a cloud platform, such as AWS or Azure. Providers are responsible for enabling
Strong-OpX to manage resources and perform operations on these platforms. Each provider
exposes a set of features. The specific features available depend on the provider.

Feature Overview
----------------
strong-opx providers expose a set of features for managing and orchestrating cloud resources. The available features
are:

- **Compute Instance Management**: Create, start, stop, and query virtual machine instances. Supports deployment using
  Ansible playbooks.
- **Kubernetes Cluster Operations**: Interact with Kubernetes clusters using `kubectl` and manage applications using
  Helm charts, without the need to manually manage kubeconfig files.
- **Container Image Building**: Build Docker images for deployment, with support for auto-tagging.
- **Variable & Secret Management**: Store variables and secrets securely inside Git repo.

Each provider may implement a subset of these features depending on its capabilities.

Supported Providers
-------------------
Currently, strong-opx supports the following cloud providers:

.. toctree::
   :maxdepth: 1

   aws
   azure

Feature Matrix
--------------
The table below summarizes which features are available for each provider:

+---------------------------------+-----+-------+
| Feature                         | AWS | Azure |
+=================================+=====+=======+
| Compute Instance Management     | Yes |  No   |
+---------------------------------+-----+-------+
| Kubernetes Cluster Operations   | Yes |  No   |
+---------------------------------+-----+-------+
| Container Image Building        | Yes |  No   |
+---------------------------------+-----+-------+
| Variable & Secret Management    | Yes | Yes   |
+---------------------------------+-----+-------+

Refer to the provider-specific documentation for more details on usage and configuration.
