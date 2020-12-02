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
Locking of Dockerfile dependencies.
"""
from __future__ import annotations

import dataclasses
from typing import List, Optional

from dlock.output import Log
from dlock.parsing import Dockerfile, FromInstruction, Instruction
from dlock.registry import Resolver


@dataclasses.dataclass(frozen=True)
class Image:
    """
    Reference to a Docker image.

    Docker repository with an optional tag, digest, or both.
    Can be converted from and to string.
    """

    repository: str
    tag: Optional[str]
    digest: Optional[str]

    def __str__(self) -> str:
        return self.to_string()

    @classmethod
    def from_string(cls, name: str) -> Image:
        tag = digest = None
        parts = name.split("@", 1)
        if len(parts) == 2:
            name, digest = parts
        parts = name.rsplit(":", 1)
        if len(parts) == 2 and "/" not in parts[1]:
            name, tag = parts
        return Image(name, tag, digest)

    def to_string(self) -> str:
        parts = [self.repository]
        if self.tag is not None:
            parts += ":", self.tag
        if self.digest is not None:
            parts += "@", self.digest
        return "".join(parts)

    def lock(self, digest: str) -> Image:
        return dataclasses.replace(self, digest=digest)


@dataclasses.dataclass
class ProcessingState:
    """
    State of Dockerfile processing.
    """

    file_name: str = "<unknown>"
    line_number: int = 0
    stages: List[str] = dataclasses.field(default_factory=list)

    #: Count of images that were newly locked
    new_count = 0
    #: Count of images that were up to date
    recent_count = 0
    #: Count of images that were upgraded
    upgrade_count = 0
    #: Count of images that were not upgraded
    keep_count = 0

    @property
    def position(self) -> str:
        return f"{self.file_name}, line {self.line_number}"


def _count_images(n: int) -> str:
    if n == 0:
        return "no base image"
    elif n == 1:
        return "one base image"
    else:
        return f"{n} base images"


class DockerfileProcessor:
    """
    Locks dependencies in a Dockerfile.
    """

    _resolver: Resolver
    _log: Log
    _upgrade: bool

    def __init__(
        self,
        resolver: Resolver,
        *,
        log: Optional[Log] = None,
        upgrade: bool = False,
    ) -> None:
        self._resolver = resolver
        self._log = Log() if log is None else log
        self._upgrade = upgrade

    def update_dockerfile(self, dockerfile: Dockerfile) -> Dockerfile:
        state = ProcessingState()
        if dockerfile.name is not None:
            state.file_name = dockerfile.name
        new_dockerfile = self._process_dockerfile(state, dockerfile)

        # Report summary of changes.
        # To ensure that at least one line of output is generated,
        # always report report locked or upgraded (depending on the upgrade flag).
        # Other numbers are reported only if non-zero.
        if state.new_count or not self._upgrade:
            count = _count_images(state.new_count)
            self._log(1, f"{state.file_name}: {count} locked")
        if state.recent_count:
            count = _count_images(state.recent_count)
            self._log(1, f"{state.file_name}: {count} up to date")
        if state.upgrade_count or self._upgrade:
            count = _count_images(state.upgrade_count)
            self._log(1, f"{state.file_name}: {count} upgraded")
        if state.keep_count:
            count = _count_images(state.keep_count)
            self._log(1, f"{state.file_name}: {count} outdated, not upgraded")
        return new_dockerfile

    def _process_dockerfile(
        self, state: ProcessingState, dockerfile: Dockerfile
    ) -> Dockerfile:
        new_instructions: List[Instruction] = []
        for state.line_number, instruction in dockerfile.with_line_numbers():
            new_instruction = self._process_instruction(state, instruction)
            new_instructions.append(new_instruction)
        return dataclasses.replace(dockerfile, instructions=new_instructions)

    def _process_instruction(
        self, state: ProcessingState, instruction: Instruction
    ) -> Instruction:
        if isinstance(instruction, FromInstruction):
            return self._process_from_instruction(state, instruction)
        return instruction

    def _process_from_instruction(
        self, state: ProcessingState, instruction: FromInstruction
    ) -> Instruction:
        new_base = self._process_ref(state, instruction.base)
        if instruction.name is not None:
            state.stages.append(instruction.name)
        return instruction.replace(base=new_base)

    def _process_ref(self, state: ProcessingState, ref: str) -> str:
        position = f"{state.position}: image {ref}"
        if "$" in ref:
            self._log(2, f"{position}: skip because it contains a variable")
            return ref
        if ref == "scratch":
            self._log(2, f"{position}: skip because scratch is a no-op")
            return ref
        if ref in state.stages:
            self._log(2, f"{position}: skip because it references a previous stage")
            return ref

        image = Image.from_string(ref)
        new_digest = self._resolver.get_digest(image.repository, image.tag)
        if image.digest is None:
            lock = True
            self._log(2, f"{position}: locked to digest {new_digest}")
            state.new_count += 1
        elif new_digest == image.digest:
            lock = False
            self._log(2, f"{position}: up to date")
            state.recent_count += 1
        elif self._upgrade:
            lock = True
            self._log(2, f"{position}: outdated, upgraded to digest {new_digest}")
            state.upgrade_count += 1
        else:
            lock = False
            self._log(2, f"{position}: outdated, not upgraded")
            state.keep_count += 1
        if lock:
            image = image.lock(new_digest)
        return image.to_string()
