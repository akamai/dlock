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

import os

import pytest

from dlock.cli import run


@pytest.fixture(name="tmp_cwd")
def tmp_cwd_fixture(tmp_path):
    orig_cwd = os.getcwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(orig_cwd)


@pytest.fixture(name="prepare_dockerfile")
def prepare_dockerfile_fixture(tmp_cwd):
    def prepare_dockerfile(content="FROM debian\n", *, name="Dockerfile"):
        path = tmp_cwd / name
        path.write_text(content)
        return path

    return prepare_dockerfile


class TestRun:
    """
    Tests the CLI entry point.
    """

    def test_lock_default_file(self, prepare_dockerfile, resolver, capsys):
        path = prepare_dockerfile()
        run([], resolver=resolver)
        assert path.read_text() == "FROM debian@sha256:81d9\n"

    def test_lock_given_file(self, prepare_dockerfile, resolver, capsys):
        path = prepare_dockerfile(name="Dockerfile.dev")
        run(["Dockerfile.dev"], resolver=resolver)
        assert path.read_text() == "FROM debian@sha256:81d9\n"

    def test_lock_multple_files(self, prepare_dockerfile, resolver, capsys):
        path1 = prepare_dockerfile(name="Dockerfile")
        path2 = prepare_dockerfile(name="Dockerfile.dev")
        run(["Dockerfile", "Dockerfile.dev"], resolver=resolver)
        assert path1.read_text() == path2.read_text() == "FROM debian@sha256:81d9\n"

    def test_upgrade_false(self, prepare_dockerfile, resolver):
        path = prepare_dockerfile("FROM debian@sha256:xxx\n")
        mtime = path.stat().st_mtime_ns
        run([], resolver=resolver)
        assert path.read_text() == "FROM debian@sha256:xxx\n"
        assert path.stat().st_mtime_ns == mtime

    def test_upgrade_true(self, prepare_dockerfile, resolver):
        path = prepare_dockerfile("FROM debian@sha256:xxx\n")
        mtime = path.stat().st_mtime_ns
        run(["--upgrade"], resolver=resolver)
        assert path.read_text() == "FROM debian@sha256:81d9\n"
        assert path.stat().st_mtime_ns > mtime

    def test_dry_run(self, prepare_dockerfile, resolver):
        path = prepare_dockerfile()
        mtime = path.stat().st_mtime_ns
        run(["--dry-run"], resolver=resolver)
        assert path.read_text() == "FROM debian\n"
        assert path.stat().st_mtime_ns == mtime

    def test_default_verbosity(self, prepare_dockerfile, resolver, capsys):
        prepare_dockerfile()
        run([], resolver=resolver)
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == (
            "Dockerfile: one base image locked\nDockerfile: changes saved\n"
        )

    def test_increased_verbosity(self, prepare_dockerfile, resolver, capsys):
        prepare_dockerfile()
        run(["--verbose"], resolver=resolver)
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == (
            "Dockerfile, line 1: image debian: locked to digest sha256:81d9\n"
            "Dockerfile: one base image locked\n"
            "Dockerfile: changes saved\n"
        )

    def test_silent_verbosity(self, prepare_dockerfile, resolver, capsys):
        prepare_dockerfile()
        run(["--silent"], resolver=resolver)
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""
