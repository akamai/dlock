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
import itertools
from abc import ABCMeta, abstractmethod
from typing import Iterable, List, Optional, Tuple

# Parsing is done in two steps:
#
# - In the first step, a Docker file is split to tokens,
#   where each token is one instruction, comment, or an empty line.
# - In the second step, a list of instructions is built from tokens.
#
# The first step is roughly based on:
# https://github.com/moby/buildkit/blob/master/frontend/dockerfile/parser/parser.go
# The second step corresponds to:
# https://github.com/moby/buildkit/blob/master/frontend/dockerfile/instructions/parse.go
#


def _is_comment_or_blank(line: str) -> bool:
    """
    Return whether the given line is a Dockerfile comment.

    Also returns true for empty lines because empty lines
    behave similar to comments (e.g. continue a command).
    """
    stripped = line.strip()
    return not stripped or stripped.startswith("#")


def _strip_line(s: str) -> str:
    """
    Strip whitespace and a possible trailing slash at the end of line.
    """
    s = s.strip()
    if s.endswith("\\"):
        s = s[:-1].rstrip()
    return s


def get_token_cmd(token: str) -> str:
    value = token.strip()
    if not value or value[0] == "#":
        return ""
    return value.split()[0].upper()


def get_token_code(token: str) -> str:
    lines = token.splitlines()
    return " ".join(
        _strip_line(line) for line in lines if not _is_comment_or_blank(line)
    )


def tokenize_dockerfile(lines: Iterable[str]) -> Iterable[str]:
    """
    Split Dockerfile to tokens.

    Each token is one instruction, comment, or an empty line.
    """
    token = ""
    for line in itertools.chain(lines, [""]):
        if not line:
            # End of file marker
            is_complete = True
        elif _is_comment_or_blank(line):
            # Comments are removed, so they do not terminate an expression.
            is_complete = not token
        else:
            # Backslash is a line continuation character.
            is_complete = not line.rstrip().endswith("\\")
        token += line
        if is_complete and token:
            yield token
            token = ""


class InvalidInstruction(Exception):
    """Instruction not understood."""


class Instruction(metaclass=ABCMeta):
    """
    Base class for Dockerfile instructions.

    Instructions are returned from the second phase of parsing.
    """

    def __str__(self) -> str:
        return self.to_string()

    @abstractmethod
    def to_string(self) -> str:
        """Return this instruction written to Dockerfile."""


@dataclasses.dataclass(frozen=True)
class FromInstruction(Instruction):
    """FROM instruction."""

    base: str
    name: Optional[str] = None
    platform: Optional[str] = None

    @classmethod
    def from_string(cls, value: str) -> FromInstruction:
        parts = get_token_code(value).split()
        # FROM ...
        if not parts or parts[0].upper() != "FROM":
            raise InvalidInstruction("Not a FROM instruction.")
        parts = parts[1:]
        # --platform=...
        platform = None
        while parts and parts[0].startswith("--"):
            if parts[0].startswith("--platform"):
                platform = parts[0][11:]
            else:
                raise InvalidInstruction(f"FROM with an unknown flag: {parts[0]}")
            parts = parts[1:]
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
class GenericInstruction(Instruction):
    """
    Instruction that we do not need to parse.

    Can be also a comment or whitespace to preserve formatting.
    """

    value: str

    def to_string(self) -> str:
        return self.value


def _parse_tokens(tokens: Iterable[str]) -> Iterable[Instruction]:
    for token in tokens:
        cmd = get_token_cmd(token)
        if cmd == "FROM":
            yield FromInstruction.from_string(token)
        else:
            yield GenericInstruction(token)


@dataclasses.dataclass(frozen=True)
class Dockerfile:
    """
    Parsed Dockerfile.

    Holds a list of parsed instructions.
    """

    instructions: List[Instruction]
    name: Optional[str] = None

    def __str__(self) -> str:
        return self.to_string()

    @classmethod
    def parse(cls, lines: Iterable[str], *, name: Optional[str] = None) -> Dockerfile:
        tokens = tokenize_dockerfile(lines)
        instructions = list(_parse_tokens(tokens))
        return cls(instructions, name=name)

    def serialize(self) -> List[str]:
        return list(map(str, self.instructions))

    def to_string(self) -> str:
        return "".join(self.serialize())

    def with_line_numbers(self) -> Iterable[Tuple[int, Instruction]]:
        line_number = 1
        for instruction in self.instructions:
            yield line_number, instruction
            line_number += instruction.to_string().count("\n")


def read_dockerfile(path: str) -> Dockerfile:
    """
    Read Dockerfile from the given file-system path.
    """
    with open(path) as f:
        return Dockerfile.parse(f, name=path)


def write_dockerfile(dockerfile: Dockerfile, path: str) -> None:
    """
    Write Dockerfile to the given file-system path.
    """
    with open(path, "w") as f:
        f.writelines(dockerfile.serialize())
