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
from __future__ import annotations

import dataclasses
from typing import List, Optional


@dataclasses.dataclass(frozen=True)
class Dockerfile:
    """
    Dockerfile content.
    """

    lines: List[str]
    name: Optional[str] = None


def read_dockerfile(path: str) -> Dockerfile:
    """
    Read Dockerfile from the given file-system path.
    """
    with open(path) as f:
        return Dockerfile(f.readlines(), name=path)


def write_dockerfile(dockerfile: Dockerfile, path: str) -> None:
    """
    Write Dockerfile to the given file-system path.
    """
    with open(path, "w") as f:
        f.writelines(dockerfile.lines)
