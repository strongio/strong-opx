Google Cloud Provider
=====================

Google Cloud provider for strong-opx allows you to manage Google Cloud resources. It currently supports only
building docker images and incrementally pushing them to Artifact Registry.

Configuration
-------------
To configure the Google Cloud provider, specify the configuration in your project config (`strong-opx.yml`).

.. code-block:: yaml

    gcloud:
      project: <project-id>                # Optional: Google Cloud Project ID
      compute_region: <region-name>        # Optional: Google Cloud region name

Additionally Google Cloud provider configuration can also be specified in an environment-specific config file
(`environments/<environment>/config.yml`). In that case the configuration from the environment file will override
the project-level configuration.
