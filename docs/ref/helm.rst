Helm Chart Config
=================

You configure Helm charts by adding YAML to your project’s
``strong-opx.yml`` file.

All possible configurations are:

.. code:: yaml

   helm:
     repos:  # Optional - Dictionary - Each key is a user-defined name of a repository and each value is the URL for that
             #                         repository. If no repos are provided, a default dictionary
             #                         of { "stable": "https://charts.helm.sh/stable" } is used.
       repo-name: https://repo/url # An example where we map the URL "https://repo/url" to a key of "repo-name"

     charts:          # Required - List - A list of charts to apply
       - name:        # Optional - String - A user-defined name used to differentiate this entry of the list from other entries
         repo:        # Required - String - The name of the repo in which a chart exists. This value must match a key defined
                      #                     in the 'helm.repos' dictionary.
         chart:       # Required - String - The name of the chart to use
         version:     # Optional - String - The version of the chart to use
         namespace:   # Optional - String - The namespace of the Kubernetes cluster which the chart should be applied to.
                      #                     This is equivalent to the '-n' or '--namespace' Helm CLI options.
         environment: # Optional - String or List of Strings - Environments this chart can be applied to
         values:      # Optional - String - Path to a file containing override values to apply to the chart. The path is
                      #                     relative to the root directory of the project and should NOT start with './'.

A real example of this is:

.. code:: yaml

   # strong-opx.yml contents; assume all other, required fields are present
   helm:
     repos:
       autoscaler: https://kubernetes.github.io/autoscaler
       spark-operator: https://googlecloudplatform.github.io/spark-on-k8s-operator

     charts:
       - name: cluster-autoscaler
         chart: cluster-autoscaler
         repo: autoscaler
         values: helm/cluster-autoscaler.yml

       - name: spark-operator
         chart: spark-operator
         repo: spark-operator
         values: helm/spark-operator.yml
