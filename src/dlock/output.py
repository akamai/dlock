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
