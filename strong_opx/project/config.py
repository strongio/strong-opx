import warnings
from typing import Annotated

from pydantic import BaseModel, Field, ValidationError, create_model

from strong_opx import yaml
from strong_opx.config import StrongOpxConfig
from strong_opx.helm import HelmConfig
from strong_opx.project.vars import VariableConfig
from strong_opx.providers import Provider, SecretProvider, select_provider
from strong_opx.utils.validation import translate_pydantic_errors


class ProjectConfig(BaseModel):
    name: str
    dirname: str = None

    provider: Provider
    strong_opx: StrongOpxConfig = None
    helm: HelmConfig = None

    secret: SecretProvider = SecretProvider()
    vars: VariableConfig

    @classmethod
    def from_file(cls, config_path: str) -> "ProjectConfig":
        config_dict = yaml.load(config_path)
        if config_dict.pop("version", None) is not None:
            warnings.warn(f"`version` is deprecated. Remove this from {config_path} to dismiss this warning")

        provider_name, provider_class = select_provider(config_dict)

        project_config_cls = create_model(
            "GeneratedProjectConfig",
            provider=Annotated[provider_class, Field(alias=provider_name)],
            __base__=cls,
        )

        try:
            return project_config_cls(**config_dict)
        except ValidationError as ex:
            raise translate_pydantic_errors(config_dict, ex)
