from functools import cached_property
from typing import TYPE_CHECKING, Callable

from strong_opx.providers import Provider
from strong_opx.providers.gcloud.context_hooks import update_environ_hook
from strong_opx.providers.gcloud.credentials import GCloudConfig

if TYPE_CHECKING:
    from strong_opx.template import Context


class GCloudProvider(Provider):
    config: GCloudConfig
    compute_instance_id_re = r"^i-[0-9a-f]+$"

    @cached_property
    def gcp_project_path(self):
        return f"projects/{self.config.project}/locations/{self.config.compute_region}"

    def get_additional_context_hooks(self) -> tuple[Callable[["Context"], None], ...]:
        return (
            self.update_context,
            update_environ_hook,
        )

    def update_context(self, context: "Context"):
        context.update(self.config.dict())
