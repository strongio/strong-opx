Strong-OpX Environment Specific Configuration
=============================================

+---------------------------------+-----------------------+-----------------------+
| Key                             | Expected Value        | Description           |
+=================================+=======================+=======================+
| ``ssh.user``                    | user to log in as     | Specifies the user to |
|                                 |                       | log in as on the      |
|                                 |                       | remote machine        |
|                                 |                       | (Required)            |
+---------------------------------+-----------------------+-----------------------+
| ``ssh.key``                     | Path to RSA private   | File from which the   |
|                                 | Key                   | private key for       |
|                                 |                       | public key            |
|                                 |                       | authentication is     |
|                                 |                       | read (Required)       |
+---------------------------------+-----------------------+-----------------------+
| ``git.ssh.key``                 | Path to RSA private   | SSH key to use for    |
|                                 | Key                   | pulling source code   |
|                                 |                       | during deployment.    |
|                                 |                       | Defaults to           |
|                                 |                       | ``ssh.key``           |
+---------------------------------+-----------------------+-----------------------+
| ``terraform.executable``        | Executable Path       | Path to terraform     |
|                                 |                       | executable. Defaults  |
|                                 |                       | to ``terraform``      |
+---------------------------------+-----------------------+-----------------------+
| ``docker.executable``           | Executable Path       | Path to docker        |
|                                 |                       | executable. Defaults  |
|                                 |                       | to ``docker``         |
+---------------------------------+-----------------------+-----------------------+
| ``ansible.playbook.executable`` | Executable Path       | Path to               |
|                                 |                       | ansible-playbook      |
|                                 |                       | executable. Defaults  |
|                                 |                       | to                    |
|                                 |                       | ``ansible-playbook``  |
+---------------------------------+-----------------------+-----------------------+
| ``aws.aws_profile``             | AWS profile name      | Name of AWS profile   |
|                                 |                       | name to use           |
+---------------------------------+-----------------------+-----------------------+
| ``kubectl.executable``          | Executable Path       | Path to kubectl       |
|                                 |                       | executable. Defaults  |
|                                 |                       | to ``docker``         |
+---------------------------------+-----------------------+-----------------------+
