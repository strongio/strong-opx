from pydantic.dataclasses import dataclass

from strong_opx.exceptions import ImproperlyConfiguredError


@dataclass
class GCloudConfig:
    project: str = None
    compute_region: str = None

    def dict(self):
        d = {}
        if self.project:
            d["CLOUDSDK_CORE_PROJECT"] = self.project
        else:
            raise ImproperlyConfiguredError(
                "GCP Project ID is not configured. Either configure that in project or environment under gcloud.project"
            )

        if self.compute_region:
            d["CLOUDSDK_COMPUTE_REGION"] = self.compute_region
        else:
            raise ImproperlyConfiguredError(
                "GCP Compute Region is not configured. Either configure that in project or environment under gcloud.compute_region"
            )

        return d
