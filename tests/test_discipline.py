import pytest

from docsort.discipline import (
    build_new_filename,
    find_discipline_name,
    format_word,
    transliterate,
)


def test_transliterate():
    assert transliterate("Щука") == "schuka"
    assert transliterate("объём") == "obem"


@pytest.mark.parametrize(
    ("word", "expected"),
    [
        ("ПРИКЛАДНАЯ", "Pri"),
        ("физика", "Fiz"),
        ("Щит", "Sch"),        # многобуквенная транслитерация обрезается до 3 символов
        ("Python", "Pyt"),     # латиница не транслитерируется
        ("SQL", "Sql"),
        ("C++", "C++"),        # слово со спецсимволом остаётся целиком
        ("и", "I"),            # короткое слово
        ("Я", "Ya"),
        ("ъ", None),           # после транслитерации пусто
    ],
)
def test_format_word(word, expected):
    assert format_word(word) == expected


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("ПРИКЛАДНАЯ ФИЗИЧЕСКАЯ КУЛЬТУРА", "Progr_Pri_Fiz_Kul.pdf"),
        ("Программирование на C++", "Progr_Pro_Na_C++.pdf"),
        ("Основы Python", "Progr_Osn_Pyt.pdf"),
        ("История (России)", "Progr_Ist_Ros.pdf"),
        ("Математика", "Progr_Mat.pdf"),
    ],
)
def test_build_new_filename(name, expected):
    assert build_new_filename(name) == expected


@pytest.mark.parametrize("name", ["", "   ", "—«»", "ъ ь"])
def test_build_new_filename_empty(name):
    assert build_new_filename(name) is None


def test_find_discipline_name_basic():
    text = (
        "Министерство науки\n"
        "РАБОЧАЯ ПРОГРАММА ДИСЦИПЛИНЫ\n\n"
        "Прикладная физическая культура\n"
        "(наименование дисциплины (модуля))\n"
        "Направление подготовки 09.03.01\n"
    )
    assert find_discipline_name(text) == "Прикладная физическая культура"


def test_find_discipline_name_multiline_and_case_insensitive_marker():
    text = "Рабочая программа дисциплины\nМетоды оптимизации\nи исследование операций\n(Наименование дисциплины)"
    assert find_discipline_name(text) == "Методы оптимизации и исследование операций"


def test_find_discipline_name_limits_lines():
    text = "РАБОЧАЯ ПРОГРАММА ДИСЦИПЛИНЫ\nA\nB\nC\nD\nE"
    assert find_discipline_name(text) == "A B C"


@pytest.mark.parametrize(
    "text",
    [
        "",
        "Аннотация к курсу без маркера",
        "РАБОЧАЯ ПРОГРАММА ДИСЦИПЛИНЫ\n\n(наименование дисциплины)",
        "РАБОЧАЯ ПРОГРАММА ДИСЦИПЛИНЫ",
    ],
)
def test_find_discipline_name_not_found(text):
    assert find_discipline_name(text) is None
