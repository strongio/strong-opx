import os
from typing import Optional

from pydantic.dataclasses import dataclass

from strong_opx.exceptions import ImproperlyConfiguredError


@dataclass
class AWSConfig:
    region: Optional[str] = None

    def dict(self) -> dict[str, str]:
        d = {}
        if self.region:
            d["AWS_REGION"] = self.region

        return d


def get_aws_config(var: str, required=True) -> Optional[str]:
    var_name = f"AWS_{var.upper()}"
    value = os.getenv(var_name)
    if value is None and required:
        raise ImproperlyConfiguredError(
            f"AWS {var.capitalize()} is not configured. "
            f"Either configure that in project or environment under aws.{var.lower()}"
        )

    return value
