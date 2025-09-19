Strong OpX
==========

Welcome to the official documentation for Strong-OpX, a powerful solution developed by
`Strong Analytics <https://www.strong.io/>`_ to simplify and streamline your deployment process.
Strong-OpX acts as an intelligent wrapper around your existing tools, enhancing the management of infrastructure,
secrets, variables, and deployments. Whether you are deploying to EC2 instances or orchestrating complex
workloads on Kubernetes, Strong-OpX offers an easy-to-use interface that connects seamlessly with your
existing workflows.

Strong-OpX comes equipped with a flexible templating engine that lets you manage and inject variables across
your environments securely. It also integrates with Terraform, providing an efficient way to set up infrastructure
with reusable, shareable code across multiple environments. Key features like auto-incrementing Docker image tags,
AWS MFA-enabled access keys, and SSH capabilities ensure that Strong-OpX is both secure and efficient, whether you
are managing simple EC2 instances or large-scale Kubernetes clusters. Explore this documentation to learn how
Strong-OpX can simplify your deployment pipeline and accelerate your infrastructure management.

.. toctree::
   :maxdepth: 1
   :caption: Basics

   introduction
   installation
   cli/index

.. toctree::
   :maxdepth: 1
   :caption: References

   ref/helm
   ref/project
   ref/environment
   ref/providers/index
   ref/platforms/index
   ref/kubernetes-plugins
   ref/config
   ref/templating-language

.. toctree::
   :maxdepth: 1
   :caption: Guides

   working-with-projects
   working-with-terraform
   using-aws-profiles-with-mfa
