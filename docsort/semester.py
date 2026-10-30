"""Поиск номеров семестров в тексте рабочей программы и раскладка PDF по папкам."""

import logging
import re
import shutil
from pathlib import Path

from docsort.extractor import extract_text

logger = logging.getLogger(__name__)

MIN_SEMESTER = 1
MAX_SEMESTER = 8
MAX_RANGE_SPAN = MAX_SEMESTER  # защита от мусорных диапазонов вида "1-99"
SEMESTER_DIR_TEMPLATE = "Семестр_{}"
NO_SEMESTER_DIR = "Без_семестра"

# Число прописью -> цифра ("первом семестре", "во втором семестре")
WORD_TO_NUM = {
    "перв": 1, "втор": 2, "трет": 3, "четверт": 4,
    "пят": 5, "шест": 6, "седьм": 7, "восьм": 8,
}

# "3 семестр", "семестр 3", "в 5-м семестре"
PATTERN_DIGIT = re.compile(
    r"(?:(\d{1,2})\s*[-–]?\s*(?:й|м|ом|ым)?\s*семестр\w*)"
    r"|(?:семестр\w*\s*[№:]?\s*(\d{1,2}))",
    re.IGNORECASE,
)

# "1-3 семестрах", "семестры 1-2"
PATTERN_RANGE = re.compile(
    r"(\d{1,2})\s*[-–]\s*(\d{1,2})\s*семестр\w*"
    r"|семестр\w*\s*(\d{1,2})\s*[-–]\s*(\d{1,2})",
    re.IGNORECASE,
)

# "первом семестре", "во втором семестре"
PATTERN_WORD = re.compile(
    r"(" + "|".join(WORD_TO_NUM) + r")\w*\s+семестр\w*",
    re.IGNORECASE,
)

# "в 1, 2 семестрах", "в 1, 2, 3 семестрах 1 курса"
PATTERN_LIST = re.compile(
    r"((?:\d{1,2}\s*,\s*)+\d{1,2})\s*семестр\w*",
    re.IGNORECASE,
)


def _is_valid(num: int) -> bool:
    return MIN_SEMESTER <= num <= MAX_SEMESTER


def find_semesters(text: str) -> set[int]:
    """Найти номера семестров, упомянутые в тексте.

    Поддерживаются цифры рядом со словом «семестр», диапазоны («1-3 семестрах»),
    словесные числительные («втором семестре») и перечисления («1, 2 семестрах»).

    Args:
        text: Текст документа.

    Returns:
        Множество номеров семестров в диапазоне ``MIN_SEMESTER..MAX_SEMESTER``.
    """
    found: set[int] = set()

    for m in PATTERN_RANGE.finditer(text):
        groups = [g for g in m.groups() if g]
        start, end = int(groups[0]), int(groups[1])
        if start <= end and end - start <= MAX_RANGE_SPAN:
            found.update(n for n in range(start, end + 1) if _is_valid(n))

    for m in PATTERN_DIGIT.finditer(text):
        num_str = m.group(1) or m.group(2)
        if num_str and _is_valid(int(num_str)):
            found.add(int(num_str))

    for m in PATTERN_WORD.finditer(text):
        found.add(WORD_TO_NUM[m.group(1).lower()])

    for m in PATTERN_LIST.finditer(text):
        for n in m.group(1).split(","):
            n = n.strip()
            if n.isdigit() and _is_valid(int(n)):
                found.add(int(n))

    return found


def sort_pdfs(source: Path, output: Path) -> int:
    """Скопировать PDF из ``source`` в папки ``Семестр_N`` внутри ``output``.

    Файл, упоминающий несколько семестров, копируется в каждую папку.
    Файл без упоминаний попадает в ``Без_семестра``. Нечитаемые файлы пропускаются.

    Args:
        source: Папка с исходными PDF (без рекурсии).
        output: Папка для результата; создаётся при необходимости.

    Returns:
        Количество успешно обработанных файлов.
    """
    pdf_files = sorted(source.glob("*.pdf"))
    if not pdf_files:
        logger.warning("В папке %s не найдено PDF-файлов", source.resolve())
        return 0

    output.mkdir(parents=True, exist_ok=True)
    logger.info("Найдено %d PDF-файлов, начинаю обработку", len(pdf_files))

    processed = 0
    for pdf_path in pdf_files:
        text = extract_text(pdf_path)
        if text is None:
            continue

        semesters = sorted(find_semesters(text))
        if semesters:
            target_dirs = [output / SEMESTER_DIR_TEMPLATE.format(s) for s in semesters]
        else:
            logger.warning("%s: упоминаний семестра не найдено -> %s", pdf_path.name, NO_SEMESTER_DIR)
            target_dirs = [output / NO_SEMESTER_DIR]

        try:
            for target_dir in target_dirs:
                target_dir.mkdir(exist_ok=True)
                shutil.copy2(pdf_path, target_dir / pdf_path.name)
        except OSError as exc:
            logger.error("%s: ошибка копирования: %s", pdf_path.name, exc)
            continue

        if semesters:
            logger.info("%s -> семестры %s", pdf_path.name, semesters)
        processed += 1

    logger.info("Готово: обработано %d из %d. Результат в %s", processed, len(pdf_files), output.resolve())
    return processed
