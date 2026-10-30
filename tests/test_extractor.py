import logging
from unittest.mock import MagicMock

import pytest

from docsort import extractor


def _page(text=None, exc=None):
    page = MagicMock()
    if exc:
        page.extract_text.side_effect = exc
    else:
        page.extract_text.return_value = text
    return page


@pytest.fixture
def fake_reader(monkeypatch):
    def install(pages):
        reader = MagicMock()
        reader.pages = pages
        monkeypatch.setattr(extractor, "PdfReader", lambda _path: reader)
    return install


def test_extract_all_pages(fake_reader, tmp_path):
    fake_reader([_page("one"), _page(None), _page("three")])
    assert extractor.extract_text(tmp_path / "x.pdf") == "one\n\nthree"


def test_extract_max_pages(fake_reader, tmp_path):
    fake_reader([_page("1"), _page("2"), _page("3"), _page("4")])
    assert extractor.extract_text(tmp_path / "x.pdf", max_pages=2) == "1\n2"


def test_broken_page_is_skipped(fake_reader, tmp_path, caplog):
    fake_reader([_page("ok"), _page(exc=ValueError("bad")), _page("end")])
    with caplog.at_level(logging.WARNING):
        assert extractor.extract_text(tmp_path / "x.pdf") == "ok\nend"
    assert "страницу 2" in caplog.text


def test_unreadable_pdf_returns_none(tmp_path, caplog):
    broken = tmp_path / "broken.pdf"
    broken.write_bytes(b"not a pdf at all")
    with caplog.at_level(logging.ERROR):
        assert extractor.extract_text(broken) is None
    assert "broken.pdf" in caplog.text
