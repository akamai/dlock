import hashlib

import pytest

from dlock.registry import Resolver


class FakeResolver(Resolver):
    def get_digest(self, repository, tag=None):
        name = repository if tag is None else f"{repository}:{tag}"
        hash = hashlib.sha256(name.encode("utf-8")).hexdigest()[:4]
        return f"sha256:{hash}"


@pytest.fixture(name="resolver")
def resolver_fixture():
    return FakeResolver()
