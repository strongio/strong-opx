import os
from typing import TYPE_CHECKING

from strong_opx.exceptions import ImproperlyConfiguredError
from strong_opx.providers.aws.iam import get_current_account_id

if TYPE_CHECKING:
    from strong_opx.template import Context

AWS_CREDENTIALS_ENVIRON_KEYS = [
    "AWS_PROFILE",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
]


def import_and_clean_environ_hook(context: "Context"):
    allow_credentials = context.get("AWS_PROFILE") is None
    context["ACCOUNT_ID"] = get_current_account_id

    for k in os.environ:
        if not k.startswith("AWS_"):
            continue

        if allow_credentials and k in AWS_CREDENTIALS_ENVIRON_KEYS:
            context[k] = os.environ[k]
        else:
            del os.environ[k]


def update_environ_hook(context: "Context"):
    for k in context:
        if k.startswith("AWS_"):
            os.environ[k] = context[k]

    if "AWS_REGION" not in context:
        raise ImproperlyConfiguredError(
            "AWS Region is not configured. Either configure that in project or environment under aws.region"
        )

    os.environ["AWS_DEFAULT_REGION"] = context["AWS_REGION"]
