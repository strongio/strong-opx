Working with Terraform
======================

Strong-OpX provides a thin wrapper around terraform to make it easy to work with multiple environments and projects.

Strong-OpX encourages the use of common Terraform files. All terraform files can be placed in `terraform` folder
inside project root. However backend configuration files for each environment must be created separately.
The backend configuration files should be named ``.tfbackend`` and contain the necessary backend configuration for
that environment.

Terraform backend configuration which is specific to each environment must be placed in the plain text file
named ``.tfbackend`` inside each environment folder. This file should contain the backend configuration block
for terraform. For example, for an S3 backend, the ``.tfbackend`` file might look like this:

.. code::

   key            = "development.tfstate"
   region         = "us-east-1"


And your `main.tf` will contain other non-environment specific configuration like this:

.. code:: terraform

   terraform {
     backend "s3" {
       bucket  = "my-terraform-state-bucket"
       encrypt = true
     }
   }

Usage
-----

Before running any terraform commands, make sure to initialize the terraform by running:

.. code:: shell

   strong-opx terraform init --env my-env

And to apply the terraform configuration, run:

.. code:: shell

   strong-opx terraform apply --env my-env

All the variables mentioned in ``.tf`` will be passed to terraform via environment variables. Strong-OpX will attempt
to resolve those from ``vars`` files specified in ``strong-opx.yml``.

Similarly, you can run any terraform command as:

.. code:: shell

   strong-opx terraform <tf-command> --env my-env -- <any additional args for terraform>
