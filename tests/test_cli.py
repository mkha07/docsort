import logging

from docsort import cli, discipline, semester


def test_missing_input_dir(tmp_path):
    assert cli.main(["sort", "-i", str(tmp_path / "nope"), "-o", str(tmp_path / "out")]) == 1


def test_sort_skips_unreadable_and_continues(tmp_path, monkeypatch, caplog):
    src = tmp_path / "pdfs"
    src.mkdir()
    for name in ("a.pdf", "b.pdf", "c.pdf"):
        (src / name).write_bytes(b"%PDF-fake")
    texts = {"a.pdf": "в 1, 2 семестрах", "b.pdf": None, "c.pdf": "ничего"}
    monkeypatch.setattr(semester, "extract_text", lambda p: texts[p.name])

    out = tmp_path / "out"
    with caplog.at_level(logging.WARNING):
        assert semester.sort_pdfs(src, out) == 2
    assert (out / "Семестр_1" / "a.pdf").exists()
    assert (out / "Семестр_2" / "a.pdf").exists()
    assert (out / "Без_семестра" / "c.pdf").exists()
    assert not any(out.rglob("b.pdf"))


def test_rename_dry_run_does_not_touch_files(tmp_path, monkeypatch):
    pdf = tmp_path / "Семестр_1" / "scan_001.pdf"
    pdf.parent.mkdir()
    pdf.write_bytes(b"%PDF-fake")
    monkeypatch.setattr(
        discipline, "extract_text",
        lambda p, max_pages=None: "РАБОЧАЯ ПРОГРАММА ДИСЦИПЛИНЫ\nФизика\n(наименование дисциплины)",
    )
    assert cli.main(["rename", "-i", str(tmp_path), "--dry-run"]) == 0
    assert pdf.exists()

    assert cli.main(["rename", "-i", str(tmp_path)]) == 0
    assert (pdf.parent / "Progr_Fiz.pdf").exists()
