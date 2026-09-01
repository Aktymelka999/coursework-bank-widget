import logging
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
log_dir = project_root / 'logs'
log_dir.mkdir(exist_ok=True)

# Формат: время | модуль | уровень | сообщение
formatter = logging.Formatter(
    '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)


def _setup_logger(name: str, filename: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)  # не ниже DEBUG


    fh = logging.FileHandler(log_dir / filename, mode='w', encoding='utf-8')
    fh.setFormatter(formatter)
    fh.setLevel(logging.DEBUG)

    if not logger.handlers:
        logger.addHandler(fh)

    return logger


logger_masks = _setup_logger('masks', 'masks.log')
logger_utils = _setup_logger('utils', 'utils.log')
