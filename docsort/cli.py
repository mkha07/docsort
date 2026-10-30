"""Точка входа командной строки docsort."""

import argparse
import logging
import sys
from pathlib import Path

from docsort import __version__
from docsort.discipline import rename_pdfs
from docsort.llm import GigaChatNamer
from docsort.semester import sort_pdfs

LOG_FORMAT = "%(asctime)s %(levelname)-7s %(message)s"
LOG_DATE_FORMAT = "%H:%M:%S"


def setup_logging(verbose: bool, log_file: Path | None) -> None:
    """Настроить вывод логов в консоль и, опционально, в файл."""
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
        handlers=handlers,
        force=True,
    )
    logging.getLogger("pypdf").setLevel(logging.ERROR)


def build_parser() -> argparse.ArgumentParser:
    """Собрать парсер аргументов с подкомандами ``sort`` и ``rename``."""
    parser = argparse.ArgumentParser(
        prog="docsort",
        description="Сортировка и переименование PDF рабочих программ дисциплин.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--log-file", type=Path, help="дополнительно писать логи в файл")
    parser.add_argument("-v", "--verbose", action="store_true", help="подробный вывод (DEBUG)")

    sub = parser.add_subparsers(dest="command", required=True)

    p_sort = sub.add_parser("sort", help="разложить PDF по папкам Семестр_N")
    p_sort.add_argument("-i", "--input", type=Path, required=True, help="папка с исходными PDF")
    p_sort.add_argument("-o", "--output", type=Path, required=True, help="папка для результата")

    p_rename = sub.add_parser("rename", help="переименовать PDF в Progr_Xxx_Yyy.pdf")
    p_rename.add_argument("-i", "--input", type=Path, required=True, help="папка с PDF (рекурсивно)")
    p_rename.add_argument("--dry-run", action="store_true", help="показать изменения, ничего не меняя")
    p_rename.add_argument("--llm", action="store_true",
                          help="получать название через GigaChat (ключ в GIGACHAT_CREDENTIALS)")
    p_rename.add_argument("--verify-ssl", action="store_true",
                          help="проверять SSL-сертификат GigaChat (по умолчанию отключено: "
                               "нужен корневой сертификат Минцифры)")

    return parser


def main(argv: list[str] | None = None) -> int:
    """Запустить CLI. Возвращает код выхода."""
    args = build_parser().parse_args(argv)
    setup_logging(args.verbose, args.log_file)
    log = logging.getLogger("docsort")

    if not args.input.is_dir():
        log.error("Папка %s не найдена", args.input.resolve())
        return 1

    if args.command == "sort":
        sort_pdfs(args.input, args.output)
    elif args.command == "rename":
        namer = None
        if args.llm:
            try:
                namer = GigaChatNamer(verify_ssl=args.verify_ssl)
            except RuntimeError as exc:
                log.error("%s", exc)
                return 1
        rename_pdfs(args.input, dry_run=args.dry_run, namer=namer)
    return 0


if __name__ == "__main__":
    sys.exit(main())
