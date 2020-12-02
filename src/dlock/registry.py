"""
Resolving of Docker images in registries
"""
from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Optional, cast

from docker import DockerClient


class Resolver(metaclass=ABCMeta):
    """
    Resolves Docker image in registries.

    Abstract base class.
    """

    @abstractmethod
    def get_digest(self, repository: str, tag: Optional[str] = None) -> str:
        """Resolve image ID from the given repository"""


class DockerResolver(Resolver):
    """
    Resolves Docker image in registries using Python Docker client.
    """

    _client: DockerClient

    def __init__(self, client: DockerClient) -> None:
        self._client = client

    def get_digest(self, repository: str, tag: Optional[str] = None) -> str:
        name = repository if tag is None else f"{repository}:{tag}"
        data = self._client.images.get_registry_data(name)
        return cast(str, data.id)
