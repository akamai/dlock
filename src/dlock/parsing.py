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


def _rstrip_slash(s: str) -> str:
    """
    Remove a possible slash at the end of line.
    """
    s = s.rstrip()
    if s.endswith("\\"):
        s = s[:-1]
    return s


@dataclasses.dataclass(frozen=True)
class Token:
    """
    Token in a Docker file.

    Tokens are returned from the first phase of parsing.
    Each token corresponds to one instruction, a comment, or an empty line.
    """

    value: str

    def __str__(self) -> str:
        return self.value

    @property
    def inst(self) -> str:
        value = self.value.strip()
        if not value or value[0] == "#":
            return ""
        return value.split()[0].upper()

    @property
    def code(self) -> str:
        lines = self.value.splitlines()
        return "".join(
            _rstrip_slash(line) for line in lines if not _is_comment_or_blank(line)
        )


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

    # TODO: support the optional platform

    base: str
    name: Optional[str] = None

    @classmethod
    def from_string(cls, s: str) -> FromInstruction:
        parts = s.split()
        if len(parts) == 2:
            base = parts[1]
            name = None
        elif len(parts) == 4 and parts[2].upper() == "AS":
            _, base, _, name = parts
        else:
            raise InvalidInstruction("FROM instruction not understood.")
        return FromInstruction(base, name)

    def to_string(self) -> str:
        parts = ["FROM", self.base]
        if self.name is not None:
            parts += ["AS", self.name]
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

    def to_string(self) -> str:
        return "".join(map(str, self.instructions))

    def with_line_numbers(self) -> Iterable[Tuple[int, Instruction]]:
        line_number = 1
        for instruction in self.instructions:
            yield line_number, instruction
            line_number += instruction.to_string().count("\n")


def tokenize_dockerfile(lines: Iterable[str]) -> Iterable[Token]:
    """
    Split Dockerfile to tokens.

    Each token is one instruction, comment, or an empty line.
    """
    value = ""
    for line in itertools.chain(lines, [""]):
        is_comment = line and _is_comment_or_blank(line)
        if not is_comment and line.rstrip().endswith("\\"):
            # Backslash is a line continuation character.
            is_complete = False
        elif is_comment and value:
            # Comments are removed, so they do not terminate an expression.
            is_complete = False
        else:
            # Expression has to be complete if continuation is not indicated.
            is_complete = True
        value += line
        if is_complete and value:
            yield Token(value)
            value = ""


def _parse_tokens(tokens: Iterable[Token]) -> Iterable[Instruction]:
    for token in tokens:
        if token.inst == "FROM":
            yield FromInstruction.from_string(token.code)
        else:
            yield GenericInstruction(token.value)


def parse_dockerfile(lines: Iterable[str], *, name: Optional[str] = None) -> Dockerfile:
    """
    Parse Dockerfile from its lines.
    """
    tokens = tokenize_dockerfile(lines)
    instructions = list(_parse_tokens(tokens))
    return Dockerfile(instructions, name=name)


def read_dockerfile(path: str) -> Dockerfile:
    """
    Read Dockerfile from the given file-system path.
    """
    with open(path) as f:
        return parse_dockerfile(f, name=path)


def write_dockerfile(dockerfile: Dockerfile, path: str) -> None:
    """
    Write Dockerfile to the given file-system path.
    """
    with open(path, "w") as f:
        for instruction in dockerfile.instructions:
            f.write(instruction.to_string())
