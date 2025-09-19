from typing import Optional

from pydantic.dataclasses import dataclass


@dataclass
class AzureConfig:
    resource_group: Optional[str] = None
    subscription_id: Optional[str] = None
    tenant_id: Optional[str] = None

    def dict(self) -> dict[str, str]:
        d = {}
        if self.resource_group:
            d["AZURE_RESOURCE_GROUP"] = self.resource_group

        if self.subscription_id:
            d["AZURE_SUBSCRIPTION_ID"] = self.subscription_id

        if self.tenant_id:
            d["AZURE_TENANT_ID"] = self.tenant_id

        return d
