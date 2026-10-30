import pytest

from docsort.semester import find_semesters


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Дисциплина изучается в 3 семестре.", {3}),
        ("Форма контроля: семестр 5 — экзамен.", {5}),
        ("Семестр №2", {2}),
        ("в 5-м семестре", {5}),
        ("изучается в 1-3 семестрах", {1, 2, 3}),
        ("семестры 4–6", {4, 5, 6}),
        ("в первом семестре", {1}),
        ("Во ВТОРОМ семестре", {2}),
        ("в восьмом семестре", {8}),
        ("в 1, 2 семестрах", {1, 2}),
        ("в 1, 2, 3 семестрах 1 курса", {1, 2, 3}),
        ("в 3 семестре и в четвертом семестре", {3, 4}),
    ],
)
def test_find_semesters_formats(text, expected):
    assert find_semesters(text) == expected


@pytest.mark.parametrize("text", ["", "Рабочая программа без упоминаний.", "семестр"])
def test_find_semesters_nothing_found(text):
    assert find_semesters(text) == set()


def test_find_semesters_ignores_out_of_range_numbers():
    assert find_semesters("в 12 семестре, семестр 0") == set()


def test_find_semesters_rejects_reversed_range():
    # "5-2" не является корректным диапазоном, но цифра 2 рядом со словом всё же учитывается
    assert find_semesters("5-2 семестр") == {2}
