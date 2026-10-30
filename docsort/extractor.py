"""Извлечение текста из PDF-файлов."""

import logging
from pathlib import Path

from pypdf import PdfReader

logger = logging.getLogger(__name__)


def extract_text(pdf_path: Path, max_pages: int | None = None) -> str | None:
    """Извлечь текст из PDF.

    Страницы, которые не удалось разобрать, пропускаются с предупреждением.

    Args:
        pdf_path: Путь к PDF-файлу.
        max_pages: Сколько первых страниц читать (``None`` — все).

    Returns:
        Текст документа или ``None``, если файл не удалось открыть.
    """
    try:
        reader = PdfReader(str(pdf_path))
        pages = reader.pages if max_pages is None else reader.pages[:max_pages]
        parts = []
        for page_num, page in enumerate(pages, start=1):
            try:
                parts.append(page.extract_text() or "")
            except Exception as exc:  # pypdf бросает разнородные исключения
                logger.warning("%s: не удалось прочитать страницу %d: %s", pdf_path.name, page_num, exc)
        return "\n".join(parts)
    except Exception as exc:
        logger.error("Не удалось прочитать %s: %s", pdf_path.name, exc)
        return None
