from .logger_config import logger_masks


def mask_card_number(card_full: str) -> str:
    """
    Маскирует номер карты: оставляет первые 4 и последние 4 цифры, остальное заменяет на *.
    Пример: 1234567890123456 -> 1234********3456
    """
    logger_masks.debug(f"Попытка маскирования номера: {card_full}")

    if not isinstance(card_full, str):
        logger_masks.error(f"Ожидалась строка, получено: {type(card_full)}")
        return "****"

    cleaned = card_full.replace(" ", "").replace("-", "")

    if len(cleaned) < 8:
        logger_masks.warning(
            f"Номер слишком короткий ({len(cleaned)} символов), возвращаем как есть"
        )
        return cleaned

    masked = cleaned[:4] + "*" * (len(cleaned) - 8) + cleaned[-4:]
    logger_masks.info(f"Номер успешно замаскирован: {masked}")
    return masked
