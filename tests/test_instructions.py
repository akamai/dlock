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

import pytest

from dlock.instructions import (
    CopyInstruction,
    FromInstruction,
    GenericInstruction,
    InvalidInstruction,
    get_token_cmd,
    split_token,
)


class TestTokenHelpers:
    """
    Tests get_token_cmd and split_token.
    """

    @pytest.mark.parametrize(
        "token",
        [
            "",
            "  ",
            "\n",
            "  \n",
        ],
    )
    def test_empty(self, token):
        assert get_token_cmd(token) == ""
        assert split_token(token) == ("", {}, "")

    @pytest.mark.parametrize(
        "token",
        [
            "# Comment",
            "# Comment\n",
            "  # Comment\n",
        ],
    )
    def test_comment(self, token):
        assert get_token_cmd(token) == ""
        assert split_token(token) == ("", {}, "")

    @pytest.mark.parametrize(
        "token",
        [
            "FROM",
            "FROM\n",
            "FROM debian",
            "FROM debian\n",
            "  FROM debian\n",
            "from debian\n",
            "FROM debian \\\n  AS base\n",
            "FROM debian \\\n  # Comment \n AS base\n",
        ],
    )
    def test_get_token_cmd(self, token):
        assert get_token_cmd(token) == "FROM"

    def test_split_token(self):
        token = "FROM debian AS base"
        assert split_token(token) == ("FROM", {}, "debian AS base")

    def test_split_token_w_flags(self):
        token = "FROM --platform=linux/amd64 debian"
        assert split_token(token) == ("FROM", {"platform": "linux/amd64"}, "debian")

    def test_split_token_multiline(self):
        token = "FROM debian \\\n  # Comment \n  AS base\n"
        assert split_token(token) == ("FROM", {}, "debian AS base")


class TestFromInstruction:
    """
    Tests the FromInstruction class.
    """

    def test_from_string(self):
        inst = FromInstruction.from_string("FROM debian")
        assert inst == FromInstruction("debian")

    def test_from_string_w_name(self):
        inst = FromInstruction.from_string("FROM debian AS base")
        assert inst == FromInstruction("debian", "base")

    def test_from_string_w_platform(self):
        inst = FromInstruction.from_string("FROM --platform=linux/amd64 debian")
        assert inst == FromInstruction("debian", flags={"platform": "linux/amd64"})

    def test_from_string_w_name_and_platform(self):
        inst = FromInstruction.from_string("FROM --platform=linux/amd64 debian AS base")
        assert inst == FromInstruction(
            "debian", "base", flags={"platform": "linux/amd64"}
        )

    def test_from_string_lowercase(self):
        inst = FromInstruction.from_string("from debian AS base")
        assert inst == FromInstruction("debian", "base")

    def test_from_string_extra_whitespace(self):
        inst = FromInstruction.from_string("   from   debian   AS   base  ")
        assert inst == FromInstruction("debian", "base")

    @pytest.mark.parametrize(
        "token",
        [
            "",
            "X",
            "FROM",
            "FROM debian AS",
            "FROM debian X base",
            "FROM debian AS base X",
        ],
    )
    def test_from_string_invalid(self, token):
        with pytest.raises(InvalidInstruction):
            FromInstruction.from_string(token)

    def test_to_string(self):
        inst = FromInstruction("debian")
        assert str(inst) == "FROM debian\n"

    def test_to_string_w_name(self):
        inst = FromInstruction("debian", "base")
        assert str(inst) == "FROM debian AS base\n"

    def test_to_string_w_platform(self):
        inst = FromInstruction("debian", flags={"platform": "linux/amd64"})
        assert str(inst) == "FROM --platform=linux/amd64 debian\n"

    def test_to_string_w_name_and_platform(self):
        inst = FromInstruction("debian", "base", flags={"platform": "linux/amd64"})
        assert str(inst) == "FROM --platform=linux/amd64 debian AS base\n"


class TestCopyInstruction:
    """Tests the CopyInstruction class."""

    def test_from_string(self):
        inst = CopyInstruction.from_string("COPY src dst\n")
        assert inst == CopyInstruction("src dst")

    def test_from_string_json(self):
        inst = CopyInstruction.from_string('COPY ["src dir", "dst dir"]\n')
        assert inst == CopyInstruction('["src dir", "dst dir"]')

    def test_from_string_with_flag(self):
        inst = CopyInstruction.from_string("COPY --from=base src dst\n")
        assert inst == CopyInstruction("src dst", flags={"from": "base"})

    def test_from_string_lowercase(self):
        inst = CopyInstruction.from_string("copy src dst\n")
        assert inst == CopyInstruction("src dst")

    def test_from_string_extra_whitespace(self):
        inst = CopyInstruction.from_string("COPY   src   dst\n")
        assert inst == CopyInstruction("src   dst")

    @pytest.mark.parametrize(
        "token",
        [
            "",
            "X",
        ],
    )
    def test_from_string_invalid(self, token):
        with pytest.raises(InvalidInstruction):
            CopyInstruction.from_string(token)

    def test_to_string(self):
        inst = CopyInstruction("src dst")
        assert str(inst) == "COPY src dst\n"

    def test_to_string_json(self):
        inst = CopyInstruction('["src dir", "dst dir"]')
        assert str(inst) == 'COPY ["src dir", "dst dir"]\n'

    def test_to_string_with_flag(self):
        inst = CopyInstruction("src dst", flags={"from": "base"})
        assert str(inst) == "COPY --from=base src dst\n"

    def test_replace(self):
        orig_inst = CopyInstruction("src dst", flags={"from": "base"})
        inst = orig_inst.replace(from_image="base@xxxx")
        assert inst == CopyInstruction("src dst", flags={"from": "base@xxxx"})


class TestGenericInstruction:
    def test_to_string(self):
        inst = GenericInstruction("CMD echo \n  'hello world'\n")
        assert str(inst) == "CMD echo \n  'hello world'\n"
