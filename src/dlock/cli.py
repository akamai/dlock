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
Command-line interface.

Can be invoked from setuptools entry_point using dlock command,
or can be called as python -m dlock.
"""
from __future__ import annotations

import argparse
import sys
from typing import Optional, Sequence

import docker

from dlock.output import Log
from dlock.parsing import read_dockerfile, write_dockerfile
from dlock.processing import DockerfileProcessor
from dlock.registry import DockerResolver, Resolver


def run(
    args: Optional[Sequence[str]] = None,
    *,
    prog: Optional[str] = None,
    resolver: Optional[Resolver] = None,
) -> None:
    """
    Locks Docker images referenced from a Dockerfile.

    This is the main entry point of the application
    that can be called from a command line.
    """
    parser = argparse.ArgumentParser(
        prog=prog,
        description="Locks Docker images referenced from a Dockerfile.",
        allow_abbrev=False,
    )
    parser.add_argument(
        "files",
        metavar="FILE",
        nargs="*",
        default=("Dockerfile",),
        help="path to Dockerfile",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        dest="verbosity",
        action="count",
        default=1,
        help="report actions taken",
    )
    parser.add_argument(
        "-s",
        "--silent",
        dest="verbosity",
        action="store_const",
        const=0,
        help="do not produce any output",
    )
    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        default=False,
        help="do not save changes",
    )
    parser.add_argument(
        "-U",
        "--upgrade",
        action="store_true",
        default=False,
        help="upgrade dependencies that are already locked",
    )

    options = parser.parse_args(args)
    if resolver is None:
        resolver = DockerResolver(docker.from_env())
    log = Log(verbosity=options.verbosity)
    processor = DockerfileProcessor(resolver, log=log, upgrade=options.upgrade)
    for file in options.files:
        try:
            dockerfile = read_dockerfile(file)
        except OSError as e:
            log(1, f"{file}: failed to read file: {e.strerror}")
            sys.exit(1)
        new_dockerfile = processor.update_dockerfile(dockerfile)
        if new_dockerfile == dockerfile:
            log(1, f"{file}: no changes to save")
        elif options.dry_run:
            log(1, f"{file}: dry run, changes not saved")
        else:
            try:
                write_dockerfile(new_dockerfile, file)
            except OSError as e:
                log(1, f"{file}: failed write file: {e.strerror}")
                sys.exit(1)
            else:
                log(1, f"{file}: changes saved")
