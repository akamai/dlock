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

from dlock.parsing import (
    Dockerfile,
    FromInstruction,
    GenericInstruction,
    InvalidInstruction,
    get_token_cmd,
    get_token_code,
    read_dockerfile,
    tokenize_dockerfile,
    write_dockerfile,
)


class TestTokenHelpers:
    """
    Tests the Token class.
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
        assert get_token_code(token) == ""

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
        assert get_token_code(token) == ""

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

    def test_get_token_code(self):
        code = get_token_code("FROM debian \\\n  # Comment \n  AS base\n")
        assert code == "FROM debian AS base"


class TestTokenizeDockerfile:
    """
    Test the tokenize_dockerfile function.
    """

    def test_tokenize_empty(self):
        """Empty docker file."""
        assert list(tokenize_dockerfile([])) == []

    def test_tokenize_one_line_wo_trailing_newline(self):
        """Dockerfile with one line only, no new line at the end of file."""
        lines = ["# Comment"]
        assert list(tokenize_dockerfile(lines)) == ["# Comment"]

    def test_tokenize_one_line_w_trailing_newline(self):
        """Dockerfile with one line only, with new line at the end of file."""
        lines = ["# Comment\n"]
        assert list(tokenize_dockerfile(lines)) == ["# Comment\n"]

    def test_tokenize_multiple_lines_wo_trailing_newline(self):
        """Dockerfile with multiple lines, no new line at the end of file."""
        lines = ["# Comment 1\n", "# Comment 2"]
        assert list(tokenize_dockerfile(lines)) == [
            "# Comment 1\n",
            "# Comment 2",
        ]

    def test_tokenize_multiple_lines_w_trailing_newline(self):
        """Dockerfile with multiple lines, with new line at the end of file."""
        lines = ["# Comment 1\n", "# Comment 2\n"]
        assert list(tokenize_dockerfile(lines)) == [
            "# Comment 1\n",
            "# Comment 2\n",
        ]

    def test_tokenize_misc(self):
        """Simple Dockerfile with nothing tricky."""
        lines = [
            "FROM debian\n",
            "\n",
            "# Example comment\n",
            "CMD echo 'hello world'\n",
        ]
        assert list(tokenize_dockerfile(lines)) == [
            "FROM debian\n",
            "\n",
            "# Example comment\n",
            "CMD echo 'hello world'\n",
        ]

    def test_tokenize_with_leading_whitespace(self):
        """Instructions can be indented."""
        lines = [
            "  FROM debian\n",
        ]

        assert list(tokenize_dockerfile(lines)) == [
            "  FROM debian\n",
        ]

    def test_tokenize_with_trailing_whitespace(self):
        """Instructions can have trailing whitespace."""
        lines = [
            "FROM debian  \n",
        ]

        assert list(tokenize_dockerfile(lines)) == [
            "FROM debian  \n",
        ]

    def test_tokenize_lowercase_instruction(self):
        """Instructions are case insensitive."""
        lines = [
            "from debian\n",
        ]
        assert list(tokenize_dockerfile(lines)) == [
            "from debian\n",
        ]

    def test_tokenize_comment_with_trailing_slash(self):
        """Trailing slash in comments is ignored."""
        lines = [
            "# Example comment\\\n",
            "CMD echo 'hello world'\n",
        ]
        assert list(tokenize_dockerfile(lines)) == [
            "# Example comment\\\n",
            "CMD echo 'hello world'\n",
        ]

    def test_tokenize_trailing_slash(self):
        """"Backslash is a line continuation character."""
        lines = [
            "CMD echo \\\n",
            "  'hello world'\n",
        ]
        assert list(tokenize_dockerfile(lines)) == [
            "CMD echo \\\n  'hello world'\n",
        ]

    def test_tokenize_trailing_slash_followed_by_empty_line(self):
        """"Empty line as continuation is deprecated but works."""
        lines = [
            "CMD echo \\\n",
            "\n",
            "  'hello world'\n",
        ]
        assert list(tokenize_dockerfile(lines)) == [
            "CMD echo \\\n\n  'hello world'\n",
        ]

    def test_tokenize_trailing_slash_at_last_line(self):
        """"Backslash is at the last line is valid."""
        lines = [
            "CMD echo \\\n",
        ]
        assert list(tokenize_dockerfile(lines)) == [
            "CMD echo \\\n",
        ]

    def test_tokenize_trailing_slash_followed_by_comment(self):
        """Comments can be included in multi-line instructions."""
        lines = [
            "CMD echo \\\n",
            "  # Comment\n",
            "  'hello world'\n",
        ]
        assert list(tokenize_dockerfile(lines)) == [
            "CMD echo \\\n  # Comment\n  'hello world'\n",
        ]


class TestFromInstruction:
    """
    Tests Instruction subclasses.
    """

    def test_from_string(self):
        inst = FromInstruction.from_string("FROM debian")
        assert inst == FromInstruction("debian")

    def test_from_string_w_name(self):
        inst = FromInstruction.from_string("FROM debian AS base")
        assert inst == FromInstruction("debian", "base")

    def test_from_string_w_platform(self):
        inst = FromInstruction.from_string("FROM --platform=linux/amd64 debian")
        assert inst == FromInstruction("debian", platform="linux/amd64")

    def test_from_string_w_name_and_platform(self):
        inst = FromInstruction.from_string("FROM --platform=linux/amd64 debian AS base")
        assert inst == FromInstruction("debian", "base", platform="linux/amd64")

    def test_from_string_lowercase(self):
        inst = FromInstruction.from_string("from debian AS base")
        assert inst == FromInstruction("debian", "base")

    def test_from_string_extra_whitespace(self):
        inst = FromInstruction.from_string("   from   debian   AS   base  ")
        assert inst == FromInstruction("debian", "base")

    @pytest.mark.parametrize(
        "code",
        [
            "",
            "X",
            "FROM",
            "FROM debian AS",
            "FROM debian X base",
            "FROM debian AS base X",
            "FROM --foo=linux/amd64",
            "FROM --foo=linux/amd64 debian",
            "FROM --platform=linux/amd64 --foo=1",
        ],
    )
    def test_from_string_invalid(self, code):
        with pytest.raises(InvalidInstruction):
            FromInstruction.from_string(code)

    def test_to_string(self):
        inst = FromInstruction("debian")
        assert str(inst) == "FROM debian\n"

    def test_to_string_w_name(self):
        inst = FromInstruction("debian", "base")
        assert str(inst) == "FROM debian AS base\n"

    def test_to_string_w_platform(self):
        inst = FromInstruction("debian", platform="linux/amd64")
        assert str(inst) == "FROM --platform=linux/amd64 debian\n"

    def test_to_string_w_name_and_plarform(self):
        inst = FromInstruction("debian", "base", platform="linux/amd64")
        assert str(inst) == "FROM --platform=linux/amd64 debian AS base\n"


class TestGenericInstruction:
    def test_to_string(self):
        inst = GenericInstruction("CMD echo \n  'hello world'\n")
        assert str(inst) == "CMD echo \n  'hello world'\n"


class TestDockerfile:
    """
    Tests Dockerfile class.
    """

    def test_to_string(self):
        instructions = [
            FromInstruction("debian"),
            GenericInstruction("RUN \\\n  echo 'hello world'\n"),
            GenericInstruction("RUN \\\n  echo '!!!'\n"),
        ]

        assert Dockerfile(instructions).to_string() == (
            "FROM debian\n"
            "RUN \\\n"
            "  echo 'hello world'\n"
            "RUN \\\n"
            "  echo '!!!'\n"
        )

    def test_line_numbers(self):
        instructions = [
            FromInstruction("debian"),
            GenericInstruction("RUN \\\n  echo 'hello world'\n"),
            GenericInstruction("RUN \\\n  echo '!!!'\n"),
        ]
        assert list(Dockerfile(instructions).with_line_numbers()) == [
            (1, instructions[0]),
            (2, instructions[1]),
            (4, instructions[2]),
        ]


class TestParseDockerfile:
    """
    Tests the Dockerfile.parse method.
    """

    def test_no_line(self):
        """Empty Dockerfile is parsed."""
        dockerfile = Dockerfile.parse([])
        assert dockerfile.instructions == []

    def test_one_line(self):
        """Dockerfile with one line only is parsed."""
        dockerfile = Dockerfile.parse(["# Comment\n"])
        assert dockerfile.instructions == [GenericInstruction("# Comment\n")]

    def test_multiple_lines(self):
        """Dockerfile with multiple lines is parsed."""
        dockerfile = Dockerfile.parse(["# Comment 1\n", "# Comment 2\n"])
        assert dockerfile.instructions == [
            GenericInstruction("# Comment 1\n"),
            GenericInstruction("# Comment 2\n"),
        ]

    def test_parse_from_inst_wo_name(self):
        """FROM instruction without name is parsed."""
        dockerfile = Dockerfile.parse(["FROM debian"])
        assert dockerfile.instructions == [FromInstruction("debian")]

    def test_parse_from_inst_w_name(self):
        """FROM instruction with name is parsed."""
        dockerfile = Dockerfile.parse(["FROM debian AS base"])
        assert dockerfile.instructions == [FromInstruction("debian", "base")]

    def test_parse_from_inst_w_platform(self):
        """FROM instruction with platform is parsed."""
        dockerfile = Dockerfile.parse(["FROM --platform=linux/amd64 debian"])
        assert dockerfile.instructions == [
            FromInstruction("debian", platform="linux/amd64")
        ]

    def test_parse_from_inst_not_formatted(self):
        """FROM instruction is parsed even if not properly formatted."""
        dockerfile = Dockerfile.parse(["From    debian As base"])
        assert dockerfile.instructions == [FromInstruction("debian", "base")]

    def test_parse_from_inst_invalid(self):
        """FROM instruction is not parsed if not valid."""
        with pytest.raises(InvalidInstruction):
            Dockerfile.parse(["FROM"])

    @pytest.mark.parametrize(
        "value",
        [
            "\n",
            "  \n",
            "# Example comment\n",
            "CMD echo 'hello world'\n",
        ],
    )
    def test_parse_generic_instructions(self, value):
        """Most instruction are treated as unparsed strings."""
        dockerfile = Dockerfile.parse([value])
        assert dockerfile.instructions == [GenericInstruction(value)]


def test_read_dockerfile(resolver, tmp_path):
    path = tmp_path / "Dockerfile"
    path.write_text("FROM debian\n")
    dockerfile = read_dockerfile(path)
    assert dockerfile.name == path
    assert dockerfile.instructions == [FromInstruction("debian")]


def test_write_dockerfile(tmp_path):
    path = tmp_path / "Dockerfile"
    dockerfile = Dockerfile([FromInstruction("debian")])
    write_dockerfile(dockerfile, path)
    assert path.read_text() == "FROM debian\n"
