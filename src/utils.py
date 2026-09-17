import json
from datetime import datetime as real_datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, TypedDict

import pandas as pd
import requests

from .logger_config import logger_utils


class StockPriceItem(TypedDict):
    stock: str
    price: float


def load_transactions(file_path: str) -> pd.DataFrame:
    path = Path(file_path)
    logger_utils.debug(f'Попытка загрузки файла: {path}')

    if not path.exists():
        logger_utils.error(f'Файл не найден: {file_path}')
        raise FileNotFoundError(f'Файл не найден: {file_path}')

    df = pd.read_excel(path, engine='openpyxl')
    logger_utils.info(f'Загружено строк: {len(df)}')

    date_cols = ['Дата операции', 'Дата платежа']
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')

    numeric_cols = [
        'Сумма операции',
        'Кешбэк',
        'Бонусы (включая кешбэк)',
        'Округление на «Инвесткопилку»',
        'Сумма операции с округлением',
        'Сумма платежа',
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    text_cols = [
        'Категория',
        'Описание',
        'Статус',
        'MCC',
        'Валюта операции',
        'Валюта платежа',
    ]
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            df[col] = df[col].replace({'nan': None, '': None})

    card_col = 'Номер карты'
    if card_col in df.columns:
        df[card_col] = (
            df[card_col].astype(str).str.strip().replace({'nan': None, '': None})
        )

        def get_last_4(card: Optional[str]) -> Optional[str]:
            if not card:
                return None
            digits = ''.join(filter(str.isdigit, str(card)))
            return digits[-4:] if len(digits) >= 4 else digits

        df['last_digits'] = df[card_col].apply(get_last_4)

    if 'Дата операции' in df.columns:
        df = df.sort_values(by='Дата операции', ascending=False).reset_index(drop=True)

    logger_utils.info('Загрузка и обработка данных завершена')
    return df


def get_greeting(date_time_str: Optional[str] = None) -> str:
    logger_utils.debug('Вызвана функция get_greeting')

    if date_time_str is None:
        now = real_datetime.now()
    else:
        try:
            now = real_datetime.strptime(date_time_str, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            logger_utils.warning(
                'Неверный формат даты для приветствия, используем текущее время'
            )
            now = real_datetime.now()

    hour = now.hour
    if 5 <= hour < 12:
        greeting = 'Доброе утро!'
    elif 12 <= hour < 18:
        greeting = 'Добрый день!'
    elif 18 <= hour < 23:
        greeting = 'Добрый вечер!'
    else:
        greeting = 'Доброй ночи!'

    logger_utils.info(f'Сгенерировано приветствие: {greeting}')
    return greeting


def get_cards_info(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Возвращает список карт: последние 4 цифры, общие траты, кешбэк."""
    if 'last_digits' not in df.columns:
        return []

    cards: List[Dict[str, Any]] = []
    spent_col = 'Сумма операции'
    cashback_col = 'Кешбэк'

    for digits, group in df[df['last_digits'].notna()].groupby('last_digits'):
        spent = 0.0
        if spent_col in group.columns:
            spent = float(
                group[spent_col].apply(
                    lambda x: abs(x) if pd.notna(x) and x < 0 else 0
                ).sum()
            )

        cashback = 0.0
        if cashback_col in group.columns:
            cashback = float(group[cashback_col].fillna(0).sum())

        cards.append(
            {
                'last_digits': digits,
                'total_spent': round(spent, 2),
                'cashback': round(cashback, 2),
            }
        )
    return cards


def get_top_transactions(df: pd.DataFrame, n: int = 5) -> List[Dict[str, Any]]:
    """Возвращает топ-N транзакций по абсолютной сумме."""
    if 'Сумма операции' not in df.columns:
        return []

    top = df.reindex(
        df['Сумма операции'].abs().sort_values(ascending=False).index
    ).head(n)

    result: List[Dict[str, Any]] = []
    for _, row in top.iterrows():
        result.append(
            {
                'date': str(row.get('Дата операции', '')),
                'amount': round(float(abs(row['Сумма операции'])), 2),
                'category': str(row.get('Категория', '')),
                'description': str(row.get('Описание', '')),
            }
        )
    return result


def get_currency_rates(settings_file: str) -> List[Dict[str, Any]]:
    """Получает курсы валют через API на основе пользовательских настроек."""
    currencies = _load_settings(settings_file, 'user_currencies', ['USD', 'EUR'])
    rates: List[Dict[str, Any]] = []
    for currency in currencies:
        try:
            response = requests.get(
                f'https://api.exchangerate-api.com/v4/latest/{currency}',
                timeout=5,
            )
            data: Dict[str, Any] = response.json()
            rub_rate = data['rates'].get('RUB')
            if rub_rate is not None:
                rates.append({'currency': currency, 'rate': round(rub_rate, 2)})
        except Exception as e:
            logger_utils.warning(f'Не удалось получить курс для {currency}: {e}')
    return rates


def _load_settings(settings_file: str, key: str, default: List[str]) -> List[str]:
    """Читает значение из файла настроек."""
    try:
        with open(settings_file, encoding='utf-8') as f:
            settings = json.load(f)
        value = settings.get(key, default)
        # Гарантируем, что возвращаем именно List[str], даже если в JSON попало что-то другое
        if isinstance(value, list):
            return [str(item) for item in value]
        return default
    except (FileNotFoundError, json.JSONDecodeError):
        logger_utils.warning(f'Не удалось загрузить настройки из {settings_file}')
        return default


def get_stock_prices(settings_file: str) -> List[StockPriceItem]:
    """Получает цены акций через API на основе пользовательских настроек."""
    stocks = _load_settings(settings_file, 'user_stocks', [])
    prices: List[StockPriceItem] = []

    for stock in stocks:
        try:
            response = requests.get(
                f'https://query1.finance.yahoo.com/v8/finance/chart/{stock}',
                params={'interval': '1d', 'range': '1d'},
                timeout=5,
            )
            data: Dict[str, Any] = response.json()

            chart = data.get('chart')
            if not isinstance(chart, dict):
                logger_utils.warning(f'Неверный формат ответа для {stock}: нет поля chart')
                continue

            result_list = chart.get('result')
            if not isinstance(result_list, list) or len(result_list) == 0:
                logger_utils.warning(f'Нет результатов для {stock}')
                continue

            first_result = result_list[0]
            if not isinstance(first_result, dict):
                continue

            meta = first_result.get('meta')
            if not isinstance(meta, dict):
                logger_utils.warning(f'Нет meta для {stock}')
                continue

            price_raw = meta.get('regularMarketPrice')
            if price_raw is None:
                logger_utils.warning(f'Не удалось получить цену для {stock}: regularMarketPrice отсутствует')
                continue

            try:
                price_value = float(price_raw)
            except (TypeError, ValueError):
                logger_utils.warning(f'Некорректное значение цены для {stock}: {price_raw}')
                continue

            price_rounded = round(price_value, 2)

            item: StockPriceItem = {
                'stock': str(stock),
                'price': price_rounded,
            }
            prices.append(item)

        except Exception as e:
            logger_utils.warning(f'Не удалось получить цену для {stock}: {e}')

    return prices
