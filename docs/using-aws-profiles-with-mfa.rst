Using AWS Profiles with MFA
===========================

Strong-OpX supports the configuration and management of AWS profiles with MFA (Multi-Factor Authentication) enabled.
This section will guide you through setting up your AWS profiles and using them securely with Strong-OpX.

Configuring AWS Credentials
---------------------------

To configure your AWS credentials with ToolB, you will use the :doc:`./cli/aws-configure` command.
This command will prompt you to enter your AWS Access Key ID and Secret Access Key.

.. code:: shell

    strong-opx aws:configure


When executed, Strong-OpX will:

- Prompt you to enter your AWS Access Key ID and AWS Secret Access Key.
- Automatically check if MFA is enabled on your AWS account.
- If multiple MFA devices are configured, Strong-OpX will prompt you to select the MFA device you wish to use for
  authentication.

This configuration will store your AWS credentials inside `~/.aws/credentials`, allowing Strong-OpX to securely
authenticate with AWS services.

.. note::

    If MFA is enabled, profile name will be automatically postfix with `--mfa` before storing the credentials
    inside `~/.aws/credentials`.


Getting or Refreshing Temporary Credentials
-------------------------------------------

Once your AWS profile is configured, you can obtain or refresh your temporary credentials by using the
:doc:`./cli/aws-mfa` command. This command requires your MFA token and profile name as arguments.

.. code:: shell

    strong-opx aws:mfa --token <mfa-token> --profile <profile-name>

Where:

- `<profile-name>` is the name of the AWS profile you wish to use.
- `<mfa-token>` is the temporary MFA token generated from your MFA device.

Optionally, you can specify the `--duration` (in seconds) for which the temporary credentials will be valid.

This command will:

- Validate the MFA token and profile.
- Retrieve temporary security credentials with MFA protection.
- Store temporary access keys inside `~/.aws/credentials` for the specified profile.
