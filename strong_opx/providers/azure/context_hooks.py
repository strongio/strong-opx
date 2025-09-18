import os
from typing import TYPE_CHECKING

from strong_opx.exceptions import ImproperlyConfiguredError

if TYPE_CHECKING:
    from strong_opx.template import Context


def update_environ_hook(context: "Context"):
    for k in context:
        if k.startswith("AZURE_"):
            os.environ[k] = context[k]

    if "AZURE_SUBSCRIPTION_ID" not in context:
        raise ImproperlyConfiguredError(
            "Azure Subscription ID is not configured. Either configure that in project or environment under azure.subscription_id"
        )

    if "AZURE_RESOURCE_GROUP" not in context:
        raise ImproperlyConfiguredError(
            "Azure Resource Group is not configured. Either configure that in project or environment under azure.resource_group"
        )
