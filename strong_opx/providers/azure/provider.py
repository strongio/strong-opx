from typing import TYPE_CHECKING, Callable

from strong_opx.providers.azure.config import AzureConfig
from strong_opx.providers.azure.context_hooks import update_environ_hook
from strong_opx.providers.provider import Provider

if TYPE_CHECKING:
    from strong_opx.template import Context


class AzureProvider(Provider):
    config: AzureConfig

    def get_additional_context_hooks(self) -> tuple[Callable[["Context"], None], ...]:
        return (
            self.update_context,
            update_environ_hook,
        )

    def update_context(self, context: "Context"):
        context.update(self.config.dict())
