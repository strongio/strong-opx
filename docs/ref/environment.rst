Environment
===========

Configuration
-------------

.. code:: yaml

   aws: # Optional - AWS Configuration specific to environment
     region: <region-name>   # Optional: AWS region

   vars: # Optional - Additional vars for this environment
     <key>: <value>          # Required - A key value pair. Should not hold any secret info

Using Terraform to write vars
-----------------------------

As some environment variable come directly from terraform output, you
can use terraform to write config environment file on each run and
include terraform output. A practical example is:

.. code:: terraform

   resource "null_resource" "env-config" {
     triggers = {
       always_run = timestamp()
     }

     provisioner "local-exec" {
       command = <<HEREDOC
   cat<<EOF > ${path.module}/config.yml
   # Generated Code. Changes will be lost on next terraform apply
   aws:
     region: ${var.AWS_REGION}

   kubernetes:
     cluster_name: ${local.cluster_name}

   vars:
     VPC_ID: ${module.vpc.vpc_id}
     CLUSTER_NAME: ${local.cluster_name}
     PRIVATE_SUBNETS: ${join(",", local.private_subnet_names)}
     REDIS_HOST: ${aws_elasticache_cluster.redis.cache_nodes[0].address}

   hosts:
     bastion:
       - ${aws_eip.bastion_ip.public_ip}
   EOF
   HEREDOC
     }
   }

Using Common Terraform Files
----------------------------

As of v0.19.2, strong-opx now supports the use of common Terraform
files. These files must be placed in the \*-ops repo under a directory
named ``terraform``. ``strong-opx`` will check for a
``<environment>.s3.tfstate`` in the ``environments/<environment>/``
directory, and will use the common files in the ``terraform`` directory
if the tfstate file exists.

An example directory structure:

::

   my-project/
     |
     |--- environments/
     |          |
     |          |--- development/
     |                   |
     |                   |-- development.s3.tfstate
     |
     |--- terraform/
     |       |
     |       |--- main.tf
     |       |--- variables.tf
     |       | etc...
