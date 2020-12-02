from __future__ import annotations

import sys
from typing import Optional, TextIO


class Log:

    _file: TextIO
    _verbosity: int

    def __init__(self, file: Optional[TextIO] = None, verbosity: int = 0) -> None:
        if file is None:
            file = sys.stderr
        self._file = file
        self._verbosity = verbosity

    def __call__(self, verbosity: int, message: str) -> None:
        if verbosity <= self._verbosity:
            print(message, file=self._file)
