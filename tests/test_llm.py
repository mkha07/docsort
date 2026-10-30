from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from docsort import discipline
from docsort.llm import GigaChatNamer, sanitize_title


def _client(answer=None, exc=None):
    client = MagicMock()
    if exc:
        client.chat.side_effect = exc
    else:
        client.chat.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=answer))]
        )
    return client


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Прикладная физическая культура", "Progr_Prikladnaya_Fizicheskaya_Kultura.pdf"),
        ('  «Основы C++».\nПояснение', "Progr_Osnovy_C++.pdf"),
        ("a/b\\c: d", "Progr_A_B_C_D.pdf"),
        ("НЕТ", None),
        ("", None),
        ("   ", None),
    ],
)
def test_sanitize_title(raw, expected):
    assert sanitize_title(raw) == expected


def test_sanitize_title_limits_words():
    raw = " ".join(["слово"] * 20)
    assert sanitize_title(raw).count("_") == 8  # префикс + 8 слов


def test_namer_success_and_truncation():
    client = _client("Математика")
    namer = GigaChatNamer(client=client)
    assert namer("т" * 10000) == "Progr_Matematika.pdf"
    assert len(client.chat.call_args.args[0]) < 4000


def test_namer_empty_text_skips_call():
    client = _client("x")
    assert GigaChatNamer(client=client)("  ") is None
    client.chat.assert_not_called()


def test_namer_error_returns_none():
    assert GigaChatNamer(client=_client(exc=ConnectionError("down")))("текст") is None


def test_namer_requires_credentials(monkeypatch):
    monkeypatch.delenv("GIGACHAT_CREDENTIALS", raising=False)
    with pytest.raises(RuntimeError, match="GIGACHAT_CREDENTIALS"):
        GigaChatNamer()


def test_rename_uses_llm_then_falls_back(tmp_path, monkeypatch):
    for n in ("a.pdf", "b.pdf"):
        (tmp_path / n).write_bytes(b"%PDF")
    texts = {"a.pdf": "что-то", "b.pdf": "РАБОЧАЯ ПРОГРАММА ДИСЦИПЛИНЫ\nФизика\n(наименование дисциплины)"}
    monkeypatch.setattr(discipline, "extract_text", lambda p, max_pages=None: texts[p.name])
    namer = lambda text: "Progr_Himiya.pdf" if text == "что-то" else None
    discipline.rename_pdfs(tmp_path, namer=namer)
    assert (tmp_path / "Progr_Himiya.pdf").exists()
    assert (tmp_path / "Progr_Fiz.pdf").exists()
