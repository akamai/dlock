from dlock.io import Dockerfile, read_dockerfile, write_dockerfile


def test_read_dockerfile(resolver, tmp_path):
    path = tmp_path / "Dockerfile"
    path.write_text("FROM debian\n")
    dockerfile = read_dockerfile(path)
    assert dockerfile.name == path
    assert dockerfile.lines == ["FROM debian\n"]


def test_write_dockerfile(tmp_path):
    path = tmp_path / "Dockerfile"
    dockerfile = Dockerfile(["FROM debian\n"], name=path)
    write_dockerfile(dockerfile, path=dockerfile.name)
    assert path.read_text() == "FROM debian\n"
