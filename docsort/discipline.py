"""Поиск названия дисциплины, транслитерация и переименование PDF."""

import logging
import re
from collections.abc import Callable
from pathlib import Path

from docsort.extractor import extract_text
from docsort.utils import unique_path

logger = logging.getLogger(__name__)

TITLE_MARKER = "РАБОЧАЯ ПРОГРАММА ДИСЦИПЛИНЫ"
STOP_MARKER = "наименование дисциплины"  # подсказка под названием в бланке
MAX_TITLE_LINES = 3   # название обычно занимает 1-3 строки
PAGES_TO_SCAN = 3     # название обычно на первой-второй странице
PREFIX_LEN = 3        # сколько букв брать от каждого слова
FILENAME_PREFIX = "Progr_"
FILENAME_SUFFIX = ".pdf"

TRANSLIT_MAP = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}

CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]")
SYMBOL_RE = re.compile(r"[^A-Za-zА-Яа-яЁё0-9]")
# оставляем буквы, цифры и "+" (для C++)
DISALLOWED_CHARS_RE = re.compile(r"[^А-Яа-яЁёA-Za-z0-9+\s]")


def transliterate(word: str) -> str:
    """Транслитерировать русское слово в латиницу (в нижнем регистре)."""
    return "".join(TRANSLIT_MAP.get(ch, ch) for ch in word.lower())


def find_discipline_name(text: str) -> str | None:
    """Найти название дисциплины после маркера «РАБОЧАЯ ПРОГРАММА ДИСЦИПЛИНЫ».

    Собирает до ``MAX_TITLE_LINES`` непустых строк, останавливаясь
    на подсказке «(наименование дисциплины)».

    Args:
        text: Текст документа.

    Returns:
        Название дисциплины или ``None``, если найти не удалось.
    """
    idx = text.upper().find(TITLE_MARKER)
    if idx == -1:
        return None

    after = text[idx + len(TITLE_MARKER):]
    lines = [ln.strip() for ln in after.splitlines() if ln.strip()]

    collected = []
    for ln in lines:
        if STOP_MARKER in ln.lower():
            break
        collected.append(ln)
        if len(collected) >= MAX_TITLE_LINES:
            break

    return " ".join(collected) or None


def format_word(word: str) -> str | None:
    """Сократить слово названия до фрагмента имени файла.

    - Русские слова транслитерируются, берутся первые ``PREFIX_LEN`` букв.
    - Латинские слова (Python, SQL) не транслитерируются.
    - Слова со спецсимволами без кириллицы (``C++``) остаются целиком.

    Args:
        word: Одно слово названия.

    Returns:
        Фрагмент вида ``Xxx`` или ``None`` для пустого результата.
    """
    has_cyrillic = bool(CYRILLIC_RE.search(word))
    if SYMBOL_RE.search(word) and not has_cyrillic:
        return word

    prefix = (transliterate(word) if has_cyrillic else word)[:PREFIX_LEN]
    if not prefix:
        return None
    return prefix[0].upper() + prefix[1:].lower()


def build_new_filename(discipline_name: str) -> str | None:
    """Построить имя файла вида ``Progr_Xxx_Yyy_Zzz.pdf`` из названия дисциплины.

    Returns:
        Имя файла или ``None``, если в названии нет пригодных слов.
    """
    words = DISALLOWED_CHARS_RE.sub(" ", discipline_name).split()
    parts = [p for p in (format_word(w) for w in words) if p]
    if not parts:
        return None
    return FILENAME_PREFIX + "_".join(parts) + FILENAME_SUFFIX


def rename_pdfs(root: Path, dry_run: bool = False, namer: Callable[[str], str | None] | None = None) -> int:
    """Рекурсивно переименовать PDF в ``root`` по названию дисциплины.

    Args:
        root: Корневая папка (обходится рекурсивно).
        dry_run: Только показать изменения, не трогая файлы.
        namer: Необязательный генератор имени по тексту (например, GigaChat);
            при ``None`` в ответе используется эвристика.

    Returns:
        Количество переименованных (или запланированных к переименованию) файлов.
    """
    pdf_files = sorted(root.rglob("*.pdf"))
    if not pdf_files:
        logger.warning("В папке %s не найдено PDF-файлов", root.resolve())
        return 0

    mode = "ПРОБНЫЙ ПРОГОН" if dry_run else "ПЕРЕИМЕНОВАНИЕ"
    logger.info("Найдено %d PDF-файлов. Режим: %s", len(pdf_files), mode)

    renamed = 0
    for pdf_path in pdf_files:
        text = extract_text(pdf_path, max_pages=PAGES_TO_SCAN)
        if text is None:
            continue

        name = None
        new_filename = namer(text) if namer else None
        if namer and not new_filename:
            logger.warning("%s: LLM не дала название, использую эвристику", pdf_path.name)
        if not new_filename:
            name = find_discipline_name(text)
            if not name:
                logger.warning("%s: название дисциплины не найдено, пропускаю", pdf_path.name)
                continue
            new_filename = build_new_filename(name)
            if not new_filename:
                logger.warning("%s: не удалось построить имя из '%s', пропускаю", pdf_path.name, name)
                continue

        if pdf_path.name == new_filename:
            logger.info("%s: уже назван правильно", pdf_path.name)
            continue

        new_path = unique_path(pdf_path.parent / new_filename)
        logger.info("%s -> %s%s", pdf_path.name, new_path.name, f" (дисциплина: {name})" if name else "")

        if not dry_run:
            try:
                pdf_path.rename(new_path)
            except OSError as exc:
                logger.error("%s: ошибка переименования: %s", pdf_path.name, exc)
                continue
        renamed += 1

    if dry_run:
        logger.info("Пробный прогон: файлы не изменены. Запустите без --dry-run, чтобы применить.")
    else:
        logger.info("Готово: переименовано %d файлов", renamed)
    return renamed
