from docsort.utils import unique_path


def test_unique_path_free(tmp_path):
    target = tmp_path / "a.pdf"
    assert unique_path(target) == target


def test_unique_path_collisions(tmp_path):
    (tmp_path / "a.pdf").touch()
    assert unique_path(tmp_path / "a.pdf") == tmp_path / "a_2.pdf"
    (tmp_path / "a_2.pdf").touch()
    (tmp_path / "a_3.pdf").touch()
    assert unique_path(tmp_path / "a.pdf") == tmp_path / "a_4.pdf"
