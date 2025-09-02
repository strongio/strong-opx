Platform: Generic
=================

Configuration
-------------

Generic platform configuration goes inside environment config.

.. code:: yaml

   hosts:
     <host-group>: # Required - Name of host group
       - <host-ip-1>    # Required - IPv4 Address of first host in given host group
       - <host-ip-2>    # Optional - IPv4 Address of second host in given host group
       - ...
     ...

Hosts must contain atleast one host group and each host group can
atleast contain one host IP address. There is no upper bound on host
group and hosts within host group.

bastion
~~~~~~~

There is special host group named ``bastion``. It must contain only one
host and if present, all connections to hosts with private IPv4 address
will be routed via bastion server.
