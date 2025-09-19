Environment
===========

Configuration
-------------

.. code:: yaml

   vars: # Optional - Additional vars for this environment
     <key>: <value>          # Required - A key value pair. Should not hold any secret info

Environment can also hold additional configuration sections specific to provider & platform.
Check :doc:`./providers/index` and :doc:`./platforms/index` for specific configuration.

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
   cat<<EOF > ${path.module}/../environments/${var.ENVIRONMENT}/config.yml
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


.. seealso::
    - :doc:`../working-with-terraform`
