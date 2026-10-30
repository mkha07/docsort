"""Общие хелперы для работы с файловой системой."""

from pathlib import Path

FIRST_DUPLICATE_INDEX = 2


def unique_path(target: Path) -> Path:
    """Вернуть свободный путь: ``target`` или ``stem_2.ext``, ``stem_3.ext`` и т.д.

    Args:
        target: Желаемый путь к файлу.

    Returns:
        Путь, по которому файла ещё не существует.
    """
    if not target.exists():
        return target
    stem, suffix, parent = target.stem, target.suffix, target.parent
    counter = FIRST_DUPLICATE_INDEX
    while True:
        candidate = parent / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1
