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

import io

import pytest

from dlock.output import Log
from dlock.parsing import Dockerfile, FromInstruction, GenericInstruction
from dlock.processing import DockerfileProcessor, Image


class TestImage:
    """
    Tests the  Image class.
    """

    @pytest.mark.parametrize(
        "string,repository,tag,digest",
        [
            ("ubuntu", "ubuntu", None, None),
            ("ubuntu:latest", "ubuntu", "latest", None),
            ("ubuntu@sha256:fff1", "ubuntu", None, "sha256:fff1"),
            ("ubuntu:latest@sha256:fff1", "ubuntu", "latest", "sha256:fff1"),
            ("localhost:5000/ubuntu", "localhost:5000/ubuntu", None, None),
            ("localhost:5000/ubuntu:latest", "localhost:5000/ubuntu", "latest", None),
        ],
    )
    def test_from_string(self, string, repository, tag, digest):
        image = Image.from_string(string)
        assert image == Image(repository, tag, digest)

    @pytest.mark.parametrize(
        "string,repository,tag,digest",
        [
            ("ubuntu", "ubuntu", None, None),
            ("ubuntu:latest", "ubuntu", "latest", None),
            ("ubuntu@sha256:fff1", "ubuntu", None, "sha256:fff1"),
            ("ubuntu:latest@sha256:fff1", "ubuntu", "latest", "sha256:fff1"),
        ],
    )
    def test_to_string(self, string, repository, tag, digest):
        image = Image(repository, tag, digest)
        assert str(image) == string


class TestDockerfileProcessor:
    """
    Test the DockerfileProcessor class.
    """

    @pytest.mark.parametrize("upgrade", [False, True])
    def test_from(self, resolver, upgrade):
        """FROM instruction is locked."""
        processor = DockerfileProcessor(resolver, upgrade=upgrade)
        dockerfile = Dockerfile(
            [
                FromInstruction("ubuntu"),
                GenericInstruction("CMD echo 'hello world'\n"),
            ]
        )
        assert processor.update_dockerfile(dockerfile).instructions == [
            FromInstruction("ubuntu@sha256:7804"),
            GenericInstruction("CMD echo 'hello world'\n"),
        ]

    @pytest.mark.parametrize("upgrade", [False, True])
    def test_from_w_name(self, resolver, upgrade):
        """FROM instruction with name is locked."""
        processor = DockerfileProcessor(resolver, upgrade=upgrade)
        dockerfile = Dockerfile(
            [
                FromInstruction("ubuntu", "runtime"),
                GenericInstruction("CMD echo 'hello world'\n"),
            ]
        )
        assert processor.update_dockerfile(dockerfile).instructions == [
            FromInstruction("ubuntu@sha256:7804", "runtime"),
            GenericInstruction("CMD echo 'hello world'\n"),
        ]

    @pytest.mark.parametrize("upgrade", [False, True])
    def test_from_w_tag(self, resolver, upgrade):
        """FROM instruction with tag is locked."""
        processor = DockerfileProcessor(resolver, upgrade=upgrade)
        dockerfile = Dockerfile(
            [
                FromInstruction("ubuntu:latest"),
                GenericInstruction("CMD echo 'hello world'\n"),
            ]
        )
        assert processor.update_dockerfile(dockerfile).instructions == [
            FromInstruction("ubuntu:latest@sha256:abfc"),
            GenericInstruction("CMD echo 'hello world'\n"),
        ]

    def test_from_w_digest_upgrade_false(self, resolver):
        """Existing digest not is upgraded by default."""
        processor = DockerfileProcessor(resolver)
        dockerfile = Dockerfile(
            [
                FromInstruction("ubuntu@sha256:xxxx"),
                GenericInstruction("CMD echo 'hello world'\n"),
            ]
        )
        assert processor.update_dockerfile(dockerfile).instructions == [
            FromInstruction("ubuntu@sha256:xxxx"),
            GenericInstruction("CMD echo 'hello world'\n"),
        ]

    def test_from_w_digest_upgrade_true(self, resolver):
        """Existing digest is upgraded on request."""
        processor = DockerfileProcessor(resolver, upgrade=True)
        dockerfile = Dockerfile(
            [
                FromInstruction("ubuntu@sha256:xxxx"),
                GenericInstruction("CMD echo 'hello world'\n"),
            ]
        )
        assert processor.update_dockerfile(dockerfile).instructions == [
            FromInstruction("ubuntu@sha256:7804"),
            GenericInstruction("CMD echo 'hello world'\n"),
        ]

    def test_from_w_tag_and_digest_upgrade_false(self, resolver):
        """Tag with digest is not upgrade by default."""
        processor = DockerfileProcessor(resolver)
        dockerfile = Dockerfile(
            [
                FromInstruction("ubuntu:latest@sha256:xxxx"),
                GenericInstruction("CMD echo 'hello world'\n"),
            ]
        )
        assert processor.update_dockerfile(dockerfile).instructions == [
            FromInstruction("ubuntu:latest@sha256:xxxx"),
            GenericInstruction("CMD echo 'hello world'\n"),
        ]

    def test_from_w_tag_and_digest_upgrade_true(self, resolver):
        """Tag with digest is upgraded on request."""
        processor = DockerfileProcessor(resolver, upgrade=True)
        dockerfile = Dockerfile(
            [
                FromInstruction("ubuntu:latest@sha256:xxxx"),
                GenericInstruction("CMD echo 'hello world'\n"),
            ]
        )
        assert processor.update_dockerfile(dockerfile).instructions == [
            FromInstruction("ubuntu:latest@sha256:abfc"),
            GenericInstruction("CMD echo 'hello world'\n"),
        ]

    def test_from_with_arg(self, resolver):
        """Name with variable is not locked."""
        processor = DockerfileProcessor(resolver)
        dockerfile = Dockerfile(
            [
                GenericInstruction("ARG VERSION=latest\n"),
                FromInstruction("ubuntu:${VERSION}"),
                GenericInstruction("CMD echo 'hello world'\n"),
            ]
        )
        assert processor.update_dockerfile(dockerfile).instructions == [
            GenericInstruction("ARG VERSION=latest\n"),
            FromInstruction("ubuntu:${VERSION}"),
            GenericInstruction("CMD echo 'hello world'\n"),
        ]

    def test_from_scratch(self, resolver):
        """Scratch is not a real image."""
        processor = DockerfileProcessor(resolver)
        dockerfile = Dockerfile(
            [
                FromInstruction("scratch"),
            ]
        )
        assert processor.update_dockerfile(dockerfile).instructions == [
            FromInstruction("scratch"),
        ]

    def test_multi_stage(self, resolver):
        """Name of previous state is not locked."""
        processor = DockerfileProcessor(resolver)
        dockerfile = Dockerfile(
            [
                FromInstruction("ubuntu", "base"),
                FromInstruction("base"),
                GenericInstruction("CMD echo 'hello world'\n"),
            ]
        )
        assert processor.update_dockerfile(dockerfile).instructions == [
            FromInstruction("ubuntu@sha256:7804", "base"),
            FromInstruction("base"),
            GenericInstruction("CMD echo 'hello world'\n"),
        ]

    def test_output_new_image_upgrade_false(self, resolver):
        output = io.StringIO()
        processor = DockerfileProcessor(resolver, log=Log(output, verbosity=5))
        dockerfile = Dockerfile([FromInstruction("ubuntu")], name="Dockerfile")
        processor.update_dockerfile(dockerfile)
        assert output.getvalue() == (
            "Dockerfile, line 1: image ubuntu: locked to digest sha256:7804\n"
            "Dockerfile: one base image locked\n"
        )

    def test_output_outdated_image_upgrade_false(self, resolver):
        output = io.StringIO()
        processor = DockerfileProcessor(resolver, log=Log(output, verbosity=5))
        dockerfile = Dockerfile(
            [FromInstruction("ubuntu@sha256:xxx")], name="Dockerfile"
        )
        processor.update_dockerfile(dockerfile)
        assert output.getvalue() == (
            "Dockerfile, line 1: image ubuntu@sha256:xxx: outdated, not upgraded\n"
            "Dockerfile: no base image locked\n"
            "Dockerfile: one base image outdated, not upgraded\n"
        )

    def test_output_recent_image_upgrade_false(self, resolver):
        output = io.StringIO()
        processor = DockerfileProcessor(resolver, log=Log(output, verbosity=5))
        dockerfile = Dockerfile(
            [FromInstruction("ubuntu@sha256:7804")], name="Dockerfile"
        )
        processor.update_dockerfile(dockerfile)
        assert output.getvalue() == (
            "Dockerfile, line 1: image ubuntu@sha256:7804: up to date\n"
            "Dockerfile: no base image locked\n"
            "Dockerfile: one base image up to date\n"
        )

    def test_output_new_image_upgrade_true(self, resolver):
        output = io.StringIO()
        processor = DockerfileProcessor(
            resolver, upgrade=True, log=Log(output, verbosity=5)
        )

        dockerfile = Dockerfile([FromInstruction("ubuntu")], name="Dockerfile")
        processor.update_dockerfile(dockerfile)
        assert output.getvalue() == (
            "Dockerfile, line 1: image ubuntu: locked to digest sha256:7804\n"
            "Dockerfile: one base image locked\n"
            "Dockerfile: no base image upgraded\n"
        )

    def test_output_outdated_image_upgrade_true(self, resolver):
        output = io.StringIO()
        processor = DockerfileProcessor(
            resolver, upgrade=True, log=Log(output, verbosity=5)
        )
        dockerfile = Dockerfile(
            [FromInstruction("ubuntu@sha256:xxx")], name="Dockerfile"
        )
        processor.update_dockerfile(dockerfile)
        assert output.getvalue() == (
            "Dockerfile, line 1: image ubuntu@sha256:xxx:"
            " outdated, upgraded to digest sha256:7804\n"
            "Dockerfile: one base image upgraded\n"
        )

    def test_output_recent_image_upgrade_true(self, resolver):
        output = io.StringIO()
        processor = DockerfileProcessor(
            resolver, upgrade=True, log=Log(output, verbosity=5)
        )
        dockerfile = Dockerfile(
            [FromInstruction("ubuntu@sha256:7804")], name="Dockerfile"
        )
        processor.update_dockerfile(dockerfile)
        assert output.getvalue() == (
            "Dockerfile, line 1: image ubuntu@sha256:7804: up to date\n"
            "Dockerfile: one base image up to date\n"
            "Dockerfile: no base image upgraded\n"
        )
