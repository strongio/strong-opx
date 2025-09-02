from typing import TypeVar

from strong_opx.platforms.base import Platform
from strong_opx.platforms.generic import GenericPlatform
from strong_opx.platforms.kubernetes import KubernetesPlatform

ALL_PLATFORMS = [
    GenericPlatform,
    KubernetesPlatform,
]

TPlatform = TypeVar("TPlatform", bound=Platform)
