
# Dlock - Locks your Docker dependencies

Dlock allows deterministic builds of Docker images
by locking base images and making upgrades explicit.

Think of `package-lock.json`, `Pipfile.lock`, or `composer.lock` for Docker.

Dlock is hosted at [GitHub](http://github.com/akamai/dlock) and
it can be installed from [PyPI](https://pypi.org/project/dlock/).

## Introduction

Imagine that you have a `Dockerfile` for an application that runs Python 3.8:

```Dockerfile
FROM python:3.8-slim-buster
```

An image built using your Dockerfile will use the latest Python 3.8
on the latest Debian Buster as a base image. It means that
when you rebuild the image, you will get the most recent fixes
from both Python and Debian.

It is desired to promptly incorporate  all security patches,
but your build process is unpredictable:

* You have no control when your base images will be upgraded.
* You do not see a history of dependency versions used.
* You can unintentionally downgrade if you forget `docker pull`.
* It is difficult to downgrade when a problem appears.
* You still have no guarantee that your images will be rebuilt
  when a new base image is published.

This is where Dlock can help.
It locks your base image by adding a SHA-256 digest to it:

```
$ dlock
Dockerfile: one base image locked
Dockerfile: changes saved
```

```Dockerfile
FROM python:3.8-slim-buster@sha256:0944c626f71b2f44ed45c13761f3cb97d75566261ade2b2d34f6ce2987dacbcb
```

The above syntax is understood by Docker.
Docker ignores a tag when a digest is specified.

You should commit the updated Dockerfile. From now on, when you build
your image, you can be sure that the locked version will be used.

Locking your dependencies does not prevent upgrades, it makes them explicit.
When a new base image is published, you can upgrade using Dlock:

 ```
$ dlock --upgrade
Dockerfile: one base image upgraded
Dockerfile: changes saved
```

```Dockerfile
FROM python:3.8-slim-buster@sha256:b462bcd5273cc6e4afc167db410d1e113a3174c1cab6ebe946efc1d1f03a9397
```

Now you can commit your Dockerfile again,
and all future builds will use the new base image version.

With the described approach, history of all your dependencies
is tracked in a version control system,
so you can easily return to previous versions if necessary.
And because the dependencies are not upgraded randomly,
it forces to you setup a proper policy of regular upgrades.


## Installation

Dlock requires Python 3.7 or newer and can be installed using [pip]:

```shell script
pip install dlock
```


## Usage

See the command help for usage:

```shell script
dlock --help
```

## Development

* Code is formatted using [Black] and [isort].
* Style is enforced using [flake8].
* Typing is checked using [Mypy].
* Tests are run using [pytest].

[tox] is configured to run all of the above tools.

```shell script
tox
```

To run dev tools individually,
Dlock can be installed locally with dev dependencies.

```shell script
pip install --editable .[dev]
```

```shell script
black src/ tests/ && isort src/ tests/
flake8
mypy
pytest
```


## License

```
Copyright 2020 Akamai Technologies, Inc

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```

## Contributing

```
By submitting a contribution (the “Contribution”) to this project,
and for good and valuable consideration, the receipt and sufficiency of which
are hereby acknowledged, you (the “Assignor”) irrevocably convey, transfer,
and assign the Contribution to the owner of the repository (the “Assignee”),
and the Assignee hereby accepts, all of your right, title, and interest in and
to the Contribution along with all associated copyrights, copyright
registrations, and/or applications for registration and all issuances,
extensions and renewals thereof (collectively, the “Assigned Copyrights”).
You also assign all of your rights of any kind whatsoever accruing under
the Assigned Copyrights provided by applicable law of any jurisdiction,
by international treaties and conventions and otherwise throughout the world.
```


[pip]: https://pip.pypa.io
[Black]: https://black.readthedocs.io
[isort]: https://pycqa.github.io/isort/
[flake8]: https://flake8.pycqa.org
[Mypy]: http://mypy-lang.org
[pytest]: https://pytest.org/
[tox]: https://tox.readthedocs.io/
