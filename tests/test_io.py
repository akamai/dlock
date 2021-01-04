from dlock.io import Dockerfile


class TestDockerfile:
    def test_read_dockerfile(self, resolver, tmp_path):
        path = tmp_path / "Dockerfile"
        path.write_text("FROM debian\n")
        dockerfile = Dockerfile.read(path)
        assert dockerfile.name == path
        assert dockerfile.lines == ["FROM debian\n"]

    def test_write_dockerfile(self, tmp_path):
        path = tmp_path / "Dockerfile"
        dockerfile = Dockerfile(["FROM debian\n"], name=path)
        dockerfile.write()
        assert path.read_text() == "FROM debian\n"
