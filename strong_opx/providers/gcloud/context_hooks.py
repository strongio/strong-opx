import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from strong_opx.template import Context


def update_environ_hook(context: "Context"):
    # Remove all existing gcloud environment variables to avoid conflicts
    for k in os.environ:
        if k.startswith("CLOUDSDK_"):
            del os.environ[k]

    for k in context:
        if k.startswith("CLOUDSDK_"):
            os.environ[k] = context[k]
