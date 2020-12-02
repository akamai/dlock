# Copyright 2020 Akamai Technologies, Inc
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
