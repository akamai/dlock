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
)
from dlock.parsing import parse_dockerfile, tokenize_dockerfile


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


class TestParseDockerfile:
    """
    Tests the parse_dockerfile function.
    """

    def test_no_line(self):
        """Empty Dockerfile is parsed."""
        nodes = parse_dockerfile([])
        assert list(nodes) == []

    def test_one_line(self):
        """Dockerfile with one line only is parsed."""
        nodes = parse_dockerfile(["# Comment\n"])
        assert [n.inst for n in nodes] == [GenericInstruction("# Comment\n")]

    def test_multiple_lines(self):
        """Dockerfile with multiple lines is parsed."""
        nodes = parse_dockerfile(["# Comment 1\n", "# Comment 2\n"])
        assert [n.inst for n in nodes] == [
            GenericInstruction("# Comment 1\n"),
            GenericInstruction("# Comment 2\n"),
        ]

    def test_parse_from(self):
        """FROM instruction is parsed."""
        nodes = parse_dockerfile(["FROM debian"])
        assert [n.inst for n in nodes] == [FromInstruction("debian")]

    def test_parse_from_invalid(self):
        """FROM instruction is not parsed if not valid."""
        with pytest.raises(InvalidInstruction):
            list(parse_dockerfile(["FROM"]))

    def test_parse_copy(self):
        """FROM instruction is parsed."""
        nodes = parse_dockerfile(["COPY src dst"])
        assert [n.inst for n in nodes] == [CopyInstruction("src dst")]

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
        nodes = parse_dockerfile([value])
        assert [n.inst for n in nodes] == [GenericInstruction(value)]
