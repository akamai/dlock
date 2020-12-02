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
    Token,
    parse_dockerfile,
    read_dockerfile,
    tokenize_dockerfile,
    write_dockerfile,
)


class TestToken:
    """
    Tests the Token class.
    """

    @pytest.mark.parametrize(
        "value",
        [
            "",
            "  ",
            "\n",
            "  \n",
        ],
    )
    def test_empty(self, value):
        token = Token(value)
        assert token.inst == ""
        assert token.code == ""

    @pytest.mark.parametrize(
        "value",
        [
            "# Comment",
            "# Comment\n",
            "  # Comment\n",
        ],
    )
    def test_comment(self, value):
        token = Token(value)
        assert token.inst == ""
        assert token.code == ""

    @pytest.mark.parametrize(
        "value",
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
    def test_inst(self, value):
        token = Token(value)
        assert token.inst == "FROM"

    def test_code(self):
        token = Token("FROM debian \\\n  # Comment \n  AS base\n")
        assert token.code == "FROM debian   AS base"


class TestTokenizeDockerfile:
    """
    Test the tokenize_dockerfile function.
    """

    def test_tokenize_empty(self):
        """Empty docker file."""
        assert list(tokenize_dockerfile([])) == []

    def test_tokenize_one_line_wo_traling_newline(self):
        """Dockerfile with one line only, no new line at the end of file."""
        lines = ["# Comment"]
        assert list(tokenize_dockerfile(lines)) == [Token("# Comment")]

    def test_tokenize_one_line_w_traling_newline(self):
        """Dockerfile with one line only, with new line at the end of file."""
        lines = ["# Comment\n"]
        assert list(tokenize_dockerfile(lines)) == [Token("# Comment\n")]

    def test_tokenize_multiple_lines_wo_traling_newline(self):
        """Dockerfile with multiple lines, no new line at the end of file."""
        lines = ["# Comment 1\n", "# Comment 2"]
        assert list(tokenize_dockerfile(lines)) == [
            Token("# Comment 1\n"),
            Token("# Comment 2"),
        ]

    def test_tokenize_multiple_lines_w_traling_newline(self):
        """Dockerfile with multiple lines, with new line at the end of file."""
        lines = ["# Comment 1\n", "# Comment 2\n"]
        assert list(tokenize_dockerfile(lines)) == [
            Token("# Comment 1\n"),
            Token("# Comment 2\n"),
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
            Token("FROM debian\n"),
            Token("\n"),
            Token("# Example comment\n"),
            Token("CMD echo 'hello world'\n"),
        ]

    def test_tokenize_with_leading_whitespace(self):
        """Instructions can be indented."""
        lines = [
            "  FROM debian\n",
        ]

        assert list(tokenize_dockerfile(lines)) == [
            Token("  FROM debian\n"),
        ]

    def test_tokenize_with_trailing_whitespace(self):
        """Instructions can have trailing whitespace."""
        lines = [
            "FROM debian  \n",
        ]

        assert list(tokenize_dockerfile(lines)) == [
            Token("FROM debian  \n"),
        ]

    def test_tokenize_lowercase_instruction(self):
        """Instructions are case insensitive."""
        lines = [
            "from debian\n",
        ]
        assert list(tokenize_dockerfile(lines)) == [
            Token("from debian\n"),
        ]

    def test_tokenize_comment_with_trailing_slash(self):
        """Trailing slash in comments is ignored."""
        lines = [
            "# Example comment\\\n",
            "CMD echo 'hello world'\n",
        ]
        assert list(tokenize_dockerfile(lines)) == [
            Token("# Example comment\\\n"),
            Token("CMD echo 'hello world'\n"),
        ]

    def test_tokenize_trailing_slash(self):
        """"Backslash is a line continuation character."""
        lines = [
            "CMD echo \\\n",
            "  'hello world'\n",
        ]
        assert list(tokenize_dockerfile(lines)) == [
            Token("CMD echo \\\n  'hello world'\n"),
        ]

    def test_tokenize_trailing_slash_at_list_line(self):
        """"Backslash is at the last line is valid."""
        lines = [
            "CMD echo \\\n",
        ]
        assert list(tokenize_dockerfile(lines)) == [
            Token("CMD echo \\\n"),
        ]

    def test_tokenize_trailing_slash_followed_by_comment(self):
        """Comments can be included in multi-line instructions."""
        lines = [
            "CMD echo \\\n",
            "  # Comment\n" "  'hello world'\n",
        ]
        assert list(tokenize_dockerfile(lines)) == [
            Token("CMD echo \\\n  # Comment\n  'hello world'\n"),
        ]


class TestInstructions:
    """
    Tests Instruction subclasses.
    """

    def test_from_instruction_wo_name(self):
        inst = FromInstruction("debian")
        assert str(inst) == "FROM debian\n"

    def test_from_instruction_w_name(self):
        inst = FromInstruction("debian", "base")
        assert str(inst) == "FROM debian AS base\n"

    def test_generic_instruction(self):
        inst = GenericInstruction("CMD echo \n  'hello world'\n")
        assert str(inst) == "CMD echo \n  'hello world'\n"


class TestDockefile:
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
    Tests the parse_dockerfile function.
    """

    def test_no_line(self):
        """Empty Dockerfile is parsed."""
        dockerfile = parse_dockerfile([])
        assert dockerfile.instructions == []

    def test_one_line(self):
        """Dockerfile with one line only is parsed."""
        dockerfile = parse_dockerfile(["# Comment\n"])
        assert dockerfile.instructions == [GenericInstruction("# Comment\n")]

    def test_multiple_lines(self):
        """Dockerfile with multiple lines is parsed."""
        dockerfile = parse_dockerfile(["# Comment 1\n", "# Comment 2\n"])
        assert dockerfile.instructions == [
            GenericInstruction("# Comment 1\n"),
            GenericInstruction("# Comment 2\n"),
        ]

    def test_parse_from_inst_wo_name(self):
        """FROM instruction without name is parsed."""
        dockerfile = parse_dockerfile(["FROM debian"])
        assert dockerfile.instructions == [FromInstruction("debian")]

    def test_parse_from_inst_w_name(self):
        """FROM instruction with name is parsed."""
        dockerfile = parse_dockerfile(["FROM debian AS base"])
        assert dockerfile.instructions == [FromInstruction("debian", "base")]

    def test_parse_from_inst_not_formatted(self):
        """FROM instruction is parsed even if not properly formatted."""
        dockerfile = parse_dockerfile(["From    debian As base"])
        assert dockerfile.instructions == [FromInstruction("debian", "base")]

    @pytest.mark.parametrize(
        "code",
        [
            "FROM",
            "FROM debian AS",
            "FROM debian X base",
            "FROM debian AS base X",
        ],
    )
    def test_parse_from_inst_invalid(self, code):
        """FROM instruction is not parsed if not valid."""
        with pytest.raises(InvalidInstruction):
            parse_dockerfile([code])

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
        dockerfile = parse_dockerfile([value])
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
