
from datetime import datetime as real_datetime
import datetime as dt_module  # чтобы не было конфликта имён
from pathlib import Path
from typing import Optional

import pandas as pd

from .logger_config import logger_utils


def load_transactions(file_path: str) -> pd.DataFrame:
    path = Path(file_path)
    logger_utils.debug(f"Попытка загрузки файла: {path}")

    if not path.exists():
        logger_utils.error(f"Файл не найден: {file_path}")
        raise FileNotFoundError(f"Файл не найден: {file_path}")

    df = pd.read_excel(path, engine="openpyxl")
    logger_utils.info(f"Загружено строк: {len(df)}")

    if "Категория" in df.columns and len(df) > 0:
        logger_utils.info(
            f"Проверка: в файле есть категория '{df['Категория'].iloc[0]}' и '{df['Категория'].iloc[-1]}'"
        )

    date_cols = ["Дата операции", "Дата платежа"]
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    numeric_cols = [
        "Сумма операции",
        "Кешбэк",
        "Бонусы (включая кешбэк)",
        "Округление на «Инвесткопилку»",
        "Сумма операции с округлением",
        "Сумма платежа",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    text_cols = [
        "Категория",
        "Описание",
        "Статус",
        "MCC",
        "Валюта операции",
        "Валюта платежа",
    ]
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            df[col] = df[col].replace({"nan": None, "": None})

    card_col = "Номер карты"
    if card_col in df.columns:
        df[card_col] = (
            df[card_col].astype(str).str.strip().replace({"nan": None, "": None})
        )

        def get_last_4(card: Optional[str]) -> Optional[str]:
            if not card:
                return None
            digits = "".join(filter(str.isdigit, str(card)))
            return digits[-4:] if len(digits) >= 4 else digits

        df["last_digits"] = df[card_col].apply(get_last_4)

    if "Дата операции" in df.columns:
        df = df.sort_values(by="Дата операции", ascending=False).reset_index(drop=True)

    logger_utils.info("Загрузка и обработка данных завершена")
    return df


def load_transactions_dummy() -> pd.DataFrame:
    logger_utils.warning("Используется dummy-данные вместо Excel-файла")
    data = [
        {
            "Дата операции": "2023-10-01",
            "Сумма платежа": 1200.0,
            "Категория": "Продукты",
            "Описание": "Пятёрочка",
            "Карта": "Black",
        },
        {
            "Дата операции": "2023-10-02",
            "Сумма платежа": 800.0,
            "Категория": "Такси",
            "Описание": "Яндекс Такси",
            "Карта": "Platinum",
        },
        {
            "Дата операции": "2023-10-03",
            "Сумма платежа": 2500.0,
            "Категория": "Электроника",
            "Описание": "М.Видео",
            "Карта": "Black",
        },
        {
            "Дата операции": "2023-10-04",
            "Сумма платежа": 300.0,
            "Категория": "Наличные",
            "Описание": "Снятие наличных",
            "Карта": "Platinum",
        },
        {
            "Дата операции": "2023-10-05",
            "Сумма платежа": 5000.0,
            "Категория": "Пополнение счёта",
            "Описание": "Перевод себе",
            "Карта": "Black",
        },
    ]
    df = pd.DataFrame(data)
    df["Дата операции"] = pd.to_datetime(df["Дата операции"])
    return df


def load_transactions_data() -> pd.DataFrame:
    current_dir = Path(__file__).resolve().parent
    project_root = current_dir.parent
    data_path = project_root / "data" / "operations.xlsx"

    if not data_path.exists():
        raise FileNotFoundError(f"Файл не найден: {data_path}")

    df = pd.read_excel(data_path)

    required_cols = ["Сумма операции", "Категория", "Дата операции"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"В файле отсутствуют обязательные колонки: {missing_cols}")

    df["Сумма операции"] = (
        pd.to_numeric(df["Сумма операции"], errors="coerce").fillna(0)
    )
    df["Дата операции"] = pd.to_datetime(df["Дата операции"], errors="coerce")
    return df


def get_greeting(date_time_str: Optional[str] = None) -> str:
    logger_utils.debug("Вызвана функция get_greeting")

    if date_time_str is None:
        now = real_datetime.now()
    else:
        try:
            now = real_datetime.strptime(date_time_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            logger_utils.warning(
                "Неверный формат даты для приветствия, используем текущее время"
            )
            now = real_datetime.now()

    hour = now.hour
    if 5 <= hour < 12:
        greeting = "Доброе утро!"
    elif 12 <= hour < 18:
        greeting = "Добрый день!"
    elif 18 <= hour < 23:
        greeting = "Добрый вечер!"
    else:
        greeting = "Доброй ночи!"

    logger_utils.info(f"Сгенерировано приветствие: {greeting}")
    return greeting
