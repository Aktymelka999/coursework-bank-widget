import logging
from pathlib import Path


def setup_logger(name: str, log_file: str) -> logging.Logger:
    """
    Создаёт отдельный логгер для модуля.
    Файл лога перезаписывается при каждом запуске (mode='w').
    Формат: время | модуль | уровень | сообщение
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if logger.hasHandlers():
        logger.handlers.clear()

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(log_file, mode="w", encoding="utf-8")
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    return logger


project_root = Path(__file__).resolve().parent.parent
log_dir = project_root / "logs"
log_dir.mkdir(exist_ok=True)


logger_masks = setup_logger("masks", str(log_dir / "masks.log"))
logger_utils = setup_logger("utils", str(log_dir / "utils.log"))
