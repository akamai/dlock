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

from dlock.io import Dockerfile
from dlock.output import Log
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
                "FROM ubuntu\n",
                "CMD echo 'hello world'\n",
            ]
        )
        assert processor.update_dockerfile(dockerfile).lines == [
            "FROM ubuntu@sha256:7804\n",
            "CMD echo 'hello world'\n",
        ]

    @pytest.mark.parametrize("upgrade", [False, True])
    def test_from_w_name(self, resolver, upgrade):
        """FROM instruction with name is locked."""
        processor = DockerfileProcessor(resolver, upgrade=upgrade)
        dockerfile = Dockerfile(
            [
                "FROM ubuntu AS runtime\n",
                "CMD echo 'hello world'\n",
            ]
        )
        assert processor.update_dockerfile(dockerfile).lines == [
            "FROM ubuntu@sha256:7804 AS runtime\n",
            "CMD echo 'hello world'\n",
        ]

    @pytest.mark.parametrize("upgrade", [False, True])
    def test_from_w_platform(self, resolver, upgrade):
        """FROM instruction with name is locked."""
        processor = DockerfileProcessor(resolver, upgrade=upgrade)
        dockerfile = Dockerfile(
            [
                "FROM --platform=linux/amd64 ubuntu\n",
                "CMD echo 'hello world'\n",
            ]
        )
        assert processor.update_dockerfile(dockerfile).lines == [
            "FROM --platform=linux/amd64 ubuntu@sha256:7804\n",
            "CMD echo 'hello world'\n",
        ]

    @pytest.mark.parametrize("upgrade", [False, True])
    def test_from_w_tag(self, resolver, upgrade):
        """FROM instruction with tag is locked."""
        processor = DockerfileProcessor(resolver, upgrade=upgrade)
        dockerfile = Dockerfile(
            [
                "FROM ubuntu:latest\n",
                "CMD echo 'hello world'\n",
            ]
        )
        assert processor.update_dockerfile(dockerfile).lines == [
            "FROM ubuntu:latest@sha256:abfc\n",
            "CMD echo 'hello world'\n",
        ]

    def test_from_w_digest_upgrade_false(self, resolver):
        """Existing digest not is upgraded by default."""
        processor = DockerfileProcessor(resolver)
        dockerfile = Dockerfile(
            [
                "FROM ubuntu@sha256:xxxx\n",
                "CMD echo 'hello world'\n",
            ]
        )
        assert processor.update_dockerfile(dockerfile).lines == [
            "FROM ubuntu@sha256:xxxx\n",
            "CMD echo 'hello world'\n",
        ]

    def test_from_w_digest_upgrade_true(self, resolver):
        """Existing digest is upgraded on request."""
        processor = DockerfileProcessor(resolver, upgrade=True)
        dockerfile = Dockerfile(
            [
                "FROM ubuntu@sha256:xxxx\n",
                "CMD echo 'hello world'\n",
            ]
        )
        assert processor.update_dockerfile(dockerfile).lines == [
            "FROM ubuntu@sha256:7804\n",
            "CMD echo 'hello world'\n",
        ]

    def test_from_w_tag_and_digest_upgrade_false(self, resolver):
        """Tag with digest is not upgrade by default."""
        processor = DockerfileProcessor(resolver)
        dockerfile = Dockerfile(
            [
                "FROM ubuntu:latest@sha256:xxxx\n",
                "CMD echo 'hello world'\n",
            ]
        )
        assert processor.update_dockerfile(dockerfile).lines == [
            "FROM ubuntu:latest@sha256:xxxx\n",
            "CMD echo 'hello world'\n",
        ]

    def test_from_w_tag_and_digest_upgrade_true(self, resolver):
        """Tag with digest is upgraded on request."""
        processor = DockerfileProcessor(resolver, upgrade=True)
        dockerfile = Dockerfile(
            [
                "FROM ubuntu:latest@sha256:xxxx\n",
                "CMD echo 'hello world'\n",
            ]
        )
        assert processor.update_dockerfile(dockerfile).lines == [
            "FROM ubuntu:latest@sha256:abfc\n",
            "CMD echo 'hello world'\n",
        ]

    def test_from_with_arg(self, resolver):
        """Name with variable is not locked."""
        processor = DockerfileProcessor(resolver)
        dockerfile = Dockerfile(
            [
                "ARG VERSION=latest\n",
                "FROM ubuntu:${VERSION}\n",
                "CMD echo 'hello world'\n",
            ]
        )
        assert processor.update_dockerfile(dockerfile).lines == [
            "ARG VERSION=latest\n",
            "FROM ubuntu:${VERSION}\n",
            "CMD echo 'hello world'\n",
        ]

    def test_from_scratch(self, resolver):
        """Scratch is not a real image."""
        processor = DockerfileProcessor(resolver)
        dockerfile = Dockerfile(
            [
                "FROM scratch\n",
            ]
        )
        assert processor.update_dockerfile(dockerfile).lines == [
            "FROM scratch\n",
        ]

    def test_from_multi_stage(self, resolver):
        """Name of previous state is not locked."""
        processor = DockerfileProcessor(resolver)
        dockerfile = Dockerfile(
            [
                "FROM ubuntu AS base\n",
                "FROM base\n",
                "CMD echo 'hello world'\n",
            ]
        )
        assert processor.update_dockerfile(dockerfile).lines == [
            "FROM ubuntu@sha256:7804 AS base\n",
            "FROM base\n",
            "CMD echo 'hello world'\n",
        ]

    def test_from_comments_and_whitespace_preserved(self, resolver):
        """When an instruction is not changed, its formatting is preserved."""
        processor = DockerfileProcessor(resolver)
        dockerfile = Dockerfile(
            [
                "FROM \\\n",
                "    # Example comment\n",
                "    ubuntu@sha256:xxxx\n",
            ]
        )
        assert processor.update_dockerfile(dockerfile).lines == [
            "FROM \\\n",
            "    # Example comment\n",
            "    ubuntu@sha256:xxxx\n",
        ]

    def test_copy_wo_from(self, resolver):
        processor = DockerfileProcessor(resolver)
        dockerfile = Dockerfile(
            [
                "COPY src dst\n",
            ]
        )
        assert processor.update_dockerfile(dockerfile).lines == [
            "COPY src dst\n",
        ]

    def test_copy_w_from(self, resolver):
        processor = DockerfileProcessor(resolver)
        dockerfile = Dockerfile(
            [
                "COPY --from=ubuntu src dst\n",
            ]
        )
        assert processor.update_dockerfile(dockerfile).lines == [
            "COPY --from=ubuntu@sha256:7804 src dst\n",
        ]

    def test_copy_w_from_multistage(self, resolver):
        processor = DockerfileProcessor(resolver)
        dockerfile = Dockerfile(
            [
                "FROM ubuntu AS base\n",
                "FROM ubuntu\n",
                "COPY --from=base src dst\n",
            ]
        )
        assert processor.update_dockerfile(dockerfile).lines == [
            "FROM ubuntu@sha256:7804 AS base\n",
            "FROM ubuntu@sha256:7804\n",
            "COPY --from=base src dst\n",
        ]

    def test_copy_comments_and_whitespace_preserved(self, resolver):
        processor = DockerfileProcessor(resolver)
        dockerfile = Dockerfile(
            [
                "COPY \\\n",
                "    # Example comment\n",
                "    src dst\n",
            ]
        )
        assert processor.update_dockerfile(dockerfile).lines == [
            "COPY \\\n",
            "    # Example comment\n",
            "    src dst\n",
        ]

    def test_output_new_image_upgrade_false(self, resolver):
        output = io.StringIO()
        processor = DockerfileProcessor(resolver, log=Log(output, verbosity=5))
        dockerfile = Dockerfile(["FROM ubuntu"])
        processor.update_dockerfile(dockerfile)
        assert output.getvalue() == (
            "Dockerfile, line 1: image ubuntu: locked to digest sha256:7804\n"
            "Dockerfile: one base image locked\n"
        )

    def test_output_outdated_image_upgrade_false(self, resolver):
        output = io.StringIO()
        processor = DockerfileProcessor(resolver, log=Log(output, verbosity=5))
        dockerfile = Dockerfile(["FROM ubuntu@sha256:xxx"])
        processor.update_dockerfile(dockerfile)
        assert output.getvalue() == (
            "Dockerfile, line 1: image ubuntu@sha256:xxx: outdated, not upgraded\n"
            "Dockerfile: no base image locked\n"
            "Dockerfile: one base image outdated, not upgraded\n"
        )

    def test_output_recent_image_upgrade_false(self, resolver):
        output = io.StringIO()
        processor = DockerfileProcessor(resolver, log=Log(output, verbosity=5))
        dockerfile = Dockerfile(["FROM ubuntu@sha256:7804"])
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
        dockerfile = Dockerfile(["FROM ubuntu"])
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
        dockerfile = Dockerfile(["FROM ubuntu@sha256:xxx"])
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
        dockerfile = Dockerfile(["FROM ubuntu@sha256:7804"])
        processor.update_dockerfile(dockerfile)
        assert output.getvalue() == (
            "Dockerfile, line 1: image ubuntu@sha256:7804: up to date\n"
            "Dockerfile: one base image up to date\n"
            "Dockerfile: no base image upgraded\n"
        )
