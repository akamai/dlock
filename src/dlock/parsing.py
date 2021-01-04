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
from typing import Iterable

from dlock.instructions import Instruction, parse_instruction

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


def _is_command(line: str) -> bool:
    """
    Return whether the given line is a command.

    Returns False for comments and empty lines.
    Empty lines behave similar to comments,
    for example continue a multi-line command.
    """
    stripped = line.strip()
    return bool(stripped) and not stripped.startswith("#")


def tokenize_dockerfile(lines: Iterable[str]) -> Iterable[str]:
    """
    Split Dockerfile to tokens.

    Each token is one instruction, comment, or an empty line.
    """
    EOF = ""
    token = ""
    for line in itertools.chain(lines, [EOF]):
        if line == EOF:
            is_complete = True
        elif _is_command(line):
            is_complete = not line.rstrip().endswith("\\")
        else:
            is_complete = not token
        token += line
        if is_complete and token:
            yield token
            token = ""


@dataclasses.dataclass(frozen=True)
class Node:
    """Parsed instruction with some info about parsing."""

    inst: Instruction
    lineno: int
    orig: str


def parse_dockerfile(lines: Iterable[str]) -> Iterable[Node]:
    """
    Parse Dockerfile to nodes with instructions.
    """
    lineno = 1
    for token in tokenize_dockerfile(lines):
        inst = parse_instruction(token)
        yield Node(inst, lineno, token)
        lineno += token.count("\n")
