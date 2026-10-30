"""Генерация названий файлов через GigaChat (опционально, режим ``rename --llm``)."""

import logging
import os
import re

from docsort.discipline import transliterate

logger = logging.getLogger(__name__)

ENV_CREDENTIALS = "GIGACHAT_CREDENTIALS"
DEFAULT_SCOPE = "GIGACHAT_API_PERS"
DEFAULT_MODEL = "GigaChat-3-Ultra"
LLM_TEXT_LIMIT = 3000   # сколько символов начала документа отправляем в LLM
MAX_TITLE_WORDS = 8
MAX_TITLE_LEN = 80
FILENAME_PREFIX = "Progr_"
FILENAME_SUFFIX = ".pdf"

PROMPT = (
    "Ниже начало рабочей программы учебной дисциплины. Определи название дисциплины "
    "и верни ТОЛЬКО его: без кавычек, пояснений и точки, не более {n} слов, "
    "в именительном падеже, с исправленными переносами и опечатками. "
    "Если название определить невозможно, верни слово НЕТ.\n\n---\n{text}\n---"
)

_ALLOWED_RE = re.compile(r"[^А-Яа-яЁёA-Za-z0-9+\s]")


def sanitize_title(raw: str) -> str | None:
    """Превратить ответ LLM в безопасное имя файла вида ``Progr_Slovo_Slovo.pdf`` (название транслитерируется).

    Returns:
        Имя файла или ``None``, если ответ пустой или равен «НЕТ».
    """
    first_line = raw.strip().splitlines()[0] if raw.strip() else ""
    words = _ALLOWED_RE.sub(" ", first_line).split()[:MAX_TITLE_WORDS]
    if not words or (len(words) == 1 and words[0].upper() == "НЕТ"):
        return None
    title = "_".join(w[0].upper() + w[1:] for w in map(transliterate, words))[:MAX_TITLE_LEN].rstrip("_")
    return FILENAME_PREFIX + title + FILENAME_SUFFIX


def _load_dotenv() -> None:
    """Подгрузить ``.env`` из текущей папки, если установлен python-dotenv."""
    try:
        from dotenv import find_dotenv, load_dotenv
    except ImportError:
        return
    load_dotenv(find_dotenv(usecwd=True))


class GigaChatNamer:
    """Вызываемый объект: текст документа -> имя файла (или ``None``)."""

    def __init__(
        self,
        credentials: str | None = None,
        scope: str = DEFAULT_SCOPE,
        model: str = DEFAULT_MODEL,
        verify_ssl: bool = False,
        client=None,
    ):
        """
        Args:
            credentials: Ключ авторизации; по умолчанию из ``GIGACHAT_CREDENTIALS``.
            scope: Скоуп API (``GIGACHAT_API_PERS`` для физлиц).
            model: Имя модели.
            verify_ssl: Проверять ли сертификат (у GigaChat корневой сертификат Минцифры).
            client: Готовый клиент (для тестов); если не задан, создаётся из SDK.

        Raises:
            RuntimeError: Нет ключа или не установлен пакет ``gigachat``.
        """
        self._client = client
        if client is not None:
            return
        _load_dotenv()
        credentials = credentials or os.environ.get(ENV_CREDENTIALS)
        if not credentials:
            raise RuntimeError(f"Не задан ключ GigaChat: установите переменную окружения {ENV_CREDENTIALS}")
        try:
            from gigachat import GigaChat
        except ImportError as exc:
            raise RuntimeError('Не установлен пакет gigachat: pip install -e ".[llm]"') from exc
        self._client = GigaChat(
            credentials=credentials, scope=scope, model=model, verify_ssl_certs=verify_ssl
        )

    def __call__(self, text: str) -> str | None:
        """Запросить у GigaChat название дисциплины; при любой ошибке вернуть ``None``."""
        snippet = text.strip()[:LLM_TEXT_LIMIT]
        if not snippet:
            return None
        try:
            response = self._client.chat(PROMPT.format(n=MAX_TITLE_WORDS, text=snippet))
            return sanitize_title(response.choices[0].message.content)
        except Exception as exc:
            logger.warning("GigaChat недоступен или вернул ошибку: %s", exc)
            return None
