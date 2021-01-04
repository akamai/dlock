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
Dockerfile parser

Minimal necessary Dockerfile parser which looks
only for instructions that can reference Docker images.
Preserves whitespace and formatting where possible.
"""

from __future__ import annotations

import dataclasses
from abc import ABCMeta, abstractmethod
from typing import Mapping, Optional, Tuple, Type


def _strip_line(s: str) -> str:
    """
    Strip whitespace and a possible trailing slash at the end of line.
    """
    s = s.strip()
    if s.startswith("#"):
        return ""
    if s.endswith("\\"):
        s = s[:-1].rstrip()
    return s


def get_token_cmd(token: str) -> str:
    value = token.strip()
    if not value or value[0] == "#":
        return ""
    return value.split()[0].upper()


def _pop_arg(value: str) -> Tuple[str, str]:
    parts = value.split(maxsplit=1)
    head = parts[0] if len(parts) > 0 else ""
    rest = parts[1] if len(parts) > 1 else ""
    return head, rest


def split_token(token: str) -> Tuple[str, Mapping[str, str], str]:
    lines = token.splitlines()
    code = " ".join(filter(None, map(_strip_line, lines)))
    cmd, rest = _pop_arg(code)
    flags = {}
    while rest.startswith("--"):
        flag, rest = _pop_arg(rest)
        key, _, value = flag.partition("=")
        flags[key[2:]] = value
    return cmd.upper(), flags, rest


class InvalidInstruction(Exception):
    """Instruction not understood."""


class Instruction(metaclass=ABCMeta):
    """
    Base class for Dockerfile instructions.
    """

    def __str__(self) -> str:
        return self.to_string()

    @classmethod
    @abstractmethod
    def from_string(cls, token: str) -> Instruction:
        """Parse an instruction from a string."""

    @abstractmethod
    def to_string(self) -> str:
        """Serialize this instruction to a string."""


@dataclasses.dataclass(frozen=True)
class FromInstruction(Instruction):
    """FROM instruction."""

    base: str
    name: Optional[str] = None
    platform: Optional[str] = None

    @classmethod
    def from_string(cls, token: str) -> FromInstruction:
        cmd, flags, rest = split_token(token)
        if cmd != "FROM":
            raise InvalidInstruction("Not a FROM instruction.")
        platform = None
        for key, token in flags.items():
            if key == "platform":
                platform = token
            else:
                raise InvalidInstruction(f"FROM with an unknown flag: --{key}")
        parts = rest.split()
        # Base image
        if not parts:
            raise InvalidInstruction("FROM with too few arguments.")
        base = parts[0]
        parts = parts[1:]
        # Stage name
        name = None
        if len(parts) >= 2 and parts[0].upper() == "AS":
            name = parts[1]
            parts = parts[2:]
        # End of line
        if parts:
            raise InvalidInstruction("FROM with too many arguments.")
        return FromInstruction(base, name, platform=platform)

    def to_string(self) -> str:
        parts = ["FROM"]
        if self.platform is not None:
            parts.append(f"--platform={self.platform}")
        parts.append(self.base)
        if self.name is not None:
            parts.extend(["AS", self.name])
        return " ".join(parts) + "\n"

    def replace(self, *, base: str) -> FromInstruction:
        return dataclasses.replace(self, base=base)


@dataclasses.dataclass(frozen=True)
class CopyInstruction(Instruction):

    args: str
    flags: Mapping[str, str] = dataclasses.field(default_factory=dict)

    @classmethod
    def from_string(cls, token: str) -> Instruction:
        cmd, flags, args = split_token(token)
        if cmd != "COPY":
            raise InvalidInstruction("Not a COPY instruction.")
        return cls(args, flags)

    def to_string(self) -> str:
        parts = ["COPY"]
        for key, value in self.flags.items():
            parts.append(f"--{key}={value}")
        parts.append(self.args)
        return " ".join(parts) + "\n"

    def replace(self, *, from_image: str) -> CopyInstruction:
        flags = {**self.flags, "from": from_image}
        return dataclasses.replace(self, flags=flags)


@dataclasses.dataclass(frozen=True)
class GenericInstruction(Instruction):
    """
    Instruction that we do not need to parse.

    Can be also a comment or whitespace to preserve formatting.
    """

    value: str

    @classmethod
    def from_string(cls, token: str) -> GenericInstruction:
        return cls(token)

    def to_string(self) -> str:
        return self.value


INSTRUCTION_TYPES: Mapping[str, Type[Instruction]] = {
    "FROM": FromInstruction,
    "COPY": CopyInstruction,
}


def parse_instruction(token: str) -> Instruction:
    cmd = get_token_cmd(token)
    inst_cls = INSTRUCTION_TYPES.get(cmd, GenericInstruction)
    return inst_cls.from_string(token)
