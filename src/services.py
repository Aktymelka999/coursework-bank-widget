
import json
from datetime import timedelta
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd

from .logger_config import logger_utils


def _load_user_settings(settings_path: str) -> Dict[str, Any]:
    path = Path(settings_path)
    if not path.exists():
        logger_utils.warning(
            f'Файл настроек не найден: {settings_path}. Используем дефолтные.'
        )
        return {'user_currencies': ['RUB'], 'user_stocks': []}

    try:
        with path.open('r', encoding='utf-8') as f:
            data = json.load(f)
        return dict(data)
    except Exception as e:
        logger_utils.error(f'Ошибка чтения user_settings.json: {e}')
        return {'user_currencies': ['RUB'], 'user_stocks': []}


def _load_transactions_from_excel(file_path: str) -> pd.DataFrame:
    path = Path(file_path)
    logger_utils.debug(f'Загрузка транзакций из {path}')

    if not path.exists():
        logger_utils.error(f'Файл транзакций не найден: {path}')
        return pd.DataFrame()

    try:
        df = pd.read_excel(path, engine='openpyxl')
        logger_utils.info(f'Загружено строк транзакций: {len(df)}')

        rename_map = {
            'Дата операции': 'date',
            'Дата': 'date',
            'Date': 'date',
            'Сумма операции': 'amount',
            'Сумма': 'amount',
            'Amount': 'amount',
            'Валюта': 'currency',
            'Currency': 'currency',
            'Категория': 'category',
            'Category': 'category',
            'ID транзакции': 'transaction_id',
            'Transaction ID': 'transaction_id',
            'Телефон': 'phone',
            'Phone': 'phone',
            'Тип перевода': 'transfer_type',
            'Transfer Type': 'transfer_type',
            'Описание': 'description',
            'Description': 'description',
        }
        existing_cols = {k: v for k, v in rename_map.items() if k in df.columns}
        df = df.rename(columns=existing_cols)

        if 'amount' not in df.columns:
            logger_utils.warning('Нет колонки "amount". Не сможем считать кешбэк и траты.')
        if 'currency' not in df.columns:
            df['currency'] = 'RUB'
        if 'category' not in df.columns:
            df['category'] = 'Прочее'

        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
        if 'amount' in df.columns:
            df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0)

        return df
    except Exception as e:
        logger_utils.error(f'Ошибка чтения Excel: {e}')
        return pd.DataFrame()


def generate_cashback_json(
    client_id: str,
    currency: str = 'RUB',
    top_n: int = 5,
    settings_file: str = 'data/user_settings.json',
    transactions_file: str = 'data/transactions.xlsx',
) -> Dict[str, Any]:
    logger_utils.debug(
        'generate_cashback_json called',
        extra={'client_id': client_id, 'currency': currency, 'top_n': top_n},
    )

    settings = _load_user_settings(settings_file)
    user_currencies = settings.get('user_currencies', ['RUB'])
    if currency not in user_currencies:
        user_currencies.append(currency)

    df = _load_transactions_from_excel(transactions_file)

    if df.empty:
        logger_utils.warning('Транзакции не загружены. Возвращаем пустой отчёт.')
        return {
            'report_type': 'cashback_summary',
            'client_id': client_id,
            'currency': currency,
            'generated_at': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
            'cashback': {'total': 0.0, 'top_categories': [], 'transactions': []},
            'cashback_offers': [
                {
                    'offer_name': 'Кешбэк 5% на супермаркеты',
                    'category': 'Супермаркеты',
                    'category_code': 'GROCERY',
                    'rate': 0.05,
                    'cashback_percent': 5.0,
                    'valid_until': (pd.Timestamp.now() + timedelta(days=30)).strftime(
                        '%Y-%m-%d'
                    ),
                    'conditions': 'От 500 ₽, максимум 500 ₽',
                }
            ],
            'settings_used': {
                'user_currencies_in_profile': user_currencies,
                'requested_currency': currency,
                'source': 'no_data',
            },
        }

    filtered = df[df['currency'] == currency].copy()
    if filtered.empty:
        filtered = df.copy()
        logger_utils.warning(
            f'Нет транзакций в валюте {currency}. Используем смешанные валюты.'
        )

    cashback_rates = {
        'Супермаркеты': 0.05,
        'Рестораны': 0.10,
        'Такси': 0.03,
        'Электроника': 0.02,
        'АЗС': 0.04,
        'Аптеки': 0.07,
        'Одежда': 0.06,
        'Развлечения': 0.08,
    }

    def calc_cashback(row):
        rate = cashback_rates.get(row['category'], 0.01)
        amount = row['amount']

        if amount < 0:
            return round(abs(amount) * rate, 2)
        return 0.0

    filtered['cashback'] = filtered.apply(calc_cashback, axis=1)
    total_cashback = round(filtered['cashback'].sum(), 2)

    total_cashback = max(0.0, total_cashback)

    top_transactions = (
        filtered.assign(_cashback_abs=lambda x: x['cashback'].abs())
        .sort_values(by='_cashback_abs', ascending=False)
        .drop(columns=['_cashback_abs'])
        .head(top_n)
    )
    result_transactions = top_transactions.to_dict(orient='records')

    top_categories = (
        filtered.groupby('category')['cashback']
        .sum()
        .sort_values(ascending=False)
        .head(5)
        .index.tolist()
    )

    return {
        'report_type': 'cashback_summary',
        'client_id': client_id,
        'currency': currency,
        'generated_at': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
        'cashback': {
            'total': total_cashback,
            'top_categories': top_categories,
            'transactions': result_transactions,
        },
        'cashback_offers': [
            {
                'offer_name': 'Кешбэк 5% на супермаркеты',
                'category': 'Супермаркеты',
                'category_code': 'GROCERY',
                'rate': 0.05,
                'cashback_percent': 5.0,
                'valid_until': (pd.Timestamp.now() + timedelta(days=30)).strftime(
                    '%Y-%m-%d'
                ),
                'conditions': 'От 500 ₽, максимум 500 ₽',
            }
        ],
        'settings_used': {
            'user_currencies_in_profile': user_currencies,
            'requested_currency': currency,
            'source': 'transactions.xlsx',
        },
    }


def generate_main_page_json(
    date_time_str: Optional[str] = None,
    transactions_file: str = 'data/transactions.xlsx',
) -> Dict[str, Any]:
    logger_utils.debug(
        'generate_main_page_json called', extra={'date_time': date_time_str}
    )
    logger_utils.info('Генерация главной страницы на основе данных из файла')

    try:
        base_date = (
            pd.to_datetime(date_time_str) if date_time_str else pd.Timestamp.now()
        )
    except Exception:
        base_date = pd.Timestamp.now()
        logger_utils.warning(
            'Неверный формат даты для главной страницы, используем текущее время'
        )

    hour = base_date.hour
    greeting = 'Доброе утро!'
    if 12 <= hour < 18:
        greeting = 'Добрый день!'
    elif 18 <= hour < 23:
        greeting = 'Добрый вечер!'
    else:
        greeting = 'Доброй ночи!'

    df = _load_transactions_from_excel(transactions_file)

    if df.empty:
        logger_utils.warning(
            'Файл транзакций пуст или не загружен. Возвращаем нулевые значения.'
        )
        total_balance = 0.0
        pending_operations = 0
        recent_transactions: list[dict[str, Any]] = []
    else:
        total_balance = round(df['amount'].sum(), 2)
        pending_operations = 0

        recent_transactions = []
        if 'date' in df.columns and not df['date'].isna().all():
            df_sorted = df.sort_values(by='date', ascending=False)
            recent_df = df_sorted.head(3)
            for _, row in recent_df.iterrows():
                trans = {
                    'id': str(row.get('transaction_id', 'UNKNOWN')),
                    'date': (
                        row['date'].strftime('%Y-%m-%d')
                        if pd.notna(row.get('date'))
                        else 'Unknown'
                    ),
                    'category': str(row.get('category', 'Прочее')),
                    'amount': round(row['amount'], 2),
                    'currency': str(row.get('currency', 'RUB')),
                }
                recent_transactions.append(trans)

    return {
        'report_type': 'main_page',
        'greeting': greeting,
        'generated_at': base_date.strftime('%Y-%m-%d %H:%M:%S'),
        'summary': {
            'total_balance': total_balance,
            'currency': 'RUB',
            'pending_operations': pending_operations,
        },
        'recent_transactions': recent_transactions,
    }


def generate_events_page_json() -> Dict[str, Any]:
    return generate_main_page_json()


def generate_search_json(
    query: str,
    limit: int = 10,
    transactions_file: str = 'data/transactions.xlsx',
) -> Dict[str, Any]:
    logger_utils.debug(
        'generate_search_json called', extra={'query': query, 'limit': limit}
    )
    logger_utils.info(f'Поиск по запросу "{query}"')

    df = _load_transactions_from_excel(transactions_file)

    if df.empty:
        logger_utils.warning('Файл транзакций пуст. Поиск не дал результатов.')
        return {
            'report_type': 'search_results',
            'query': query,
            'limit': limit,
            'results': [],
        }

    mask = pd.Series([False] * len(df))
    if 'description' in df.columns:
        mask |= df['description'].astype(str).str.contains(query, case=False, na=False)
    if 'category' in df.columns:
        mask |= df['category'].astype(str).str.contains(query, case=False, na=False)

    found = df[mask].head(limit)

    results = []
    for _, row in found.iterrows():
        results.append(
            {
                'id': str(row.get('transaction_id', 'UNKNOWN')),
                'date': (
                    row['date'].strftime('%Y-%m-%d')
                    if 'date' in row and pd.notna(row['date'])
                    else 'Unknown'
                ),
                'category': str(row.get('category', 'Прочее')),
                'description': str(row.get('description', '')),
                'amount': round(row['amount'], 2),
                'currency': str(row.get('currency', 'RUB')),
            }
        )

    return {
        'report_type': 'search_results',
        'query': query,
        'limit': limit,
        'results': results,
    }


def generate_search_by_phone_json(
    phone: str,
    limit: int = 10,
    transactions_file: str = 'data/transactions.xlsx',
) -> dict:
    logger_utils.info(f'Поиск транзакций по телефону: {phone}, лимит: {limit}')

    df = _load_transactions_from_excel(transactions_file)

    if df.empty:
        logger_utils.warning('Нет транзакций для поиска.')
        return {
            'report_type': 'search_by_phone',
            'query': phone,
            'limit': limit,
            'results': [],
        }

    if 'phone' not in df.columns:
        logger_utils.error('Колонка "phone" не найдена в файле транзакций.')
        return {
            'report_type': 'search_by_phone',
            'query': phone,
            'limit': limit,
            'results': [],
        }

    clean_query = ''.join(filter(str.isdigit, str(phone)))

    if not clean_query:
        logger_utils.warning('В запросе не найдено цифр для поиска телефона.')
        return {
            'report_type': 'search_by_phone',
            'query': phone,
            'limit': limit,
            'results': [],
        }

    df['_phone_normalized'] = df['phone'].astype(str).str.replace(r'\D', '', regex=True)

    mask = df['_phone_normalized'] == clean_query
    filtered = df[mask].copy()

    if '_phone_normalized' in filtered.columns:
        del filtered['_phone_normalized']

    results = []
    for _, row in filtered.head(limit).iterrows():
        results.append(
            {
                'id': row.get('id'),
                'date': str(row.get('date', '')),
                'category': row.get('category'),
                'description': row.get('description', ''),
                'amount': row.get('amount'),
                'currency': row.get('currency'),
                'phone': row.get('phone'),
            }
        )

    return {
        'report_type': 'search_by_phone',
        'query': phone,
        'limit': limit,
        'results': results,
    }


def generate_transfers_to_individuals_json(
    client_id: str,
    limit: int = 10,
    transactions_file: str = 'data/transactions.xlsx',
) -> Dict[str, Any]:
    logger_utils.debug(
        'generate_transfers_to_individuals_json called',
        extra={'client_id': client_id, 'limit': limit},
    )
    logger_utils.info(f'Генерация переводов физлицам для клиента {client_id}')

    df = _load_transactions_from_excel(transactions_file)

    if df.empty:
        logger_utils.warning('Файл транзакций пуст. Переводов не найдено.')
        return {
            'report_type': 'transfers_to_individuals',
            'client_id': client_id,
            'transfers': [],
        }

    is_transfer_mask = pd.Series([False] * len(df))

    if 'category' in df.columns:
        is_transfer_mask |= df['category'].astype(str).str.lower().str.contains(
            'перевод|перевод физлицу|перевод человеку', na=False
        )

    if 'transfer_type' in df.columns:
        is_transfer_mask |= (
            df['transfer_type'].astype(str).str.lower() == 'individual'
        )

    transfers_df = df[is_transfer_mask].head(limit).copy()

    if transfers_df.empty:
        logger_utils.info('Переводы физлицам не найдены по заданным критериям.')
        return {
            'report_type': 'transfers_to_individuals',
            'client_id': client_id,
            'transfers': [],
        }

    results = []
    for _, row in transfers_df.iterrows():
        transfer_item = {
            'id': str(row.get('transaction_id', 'UNKNOWN')),
            'date': (
                row['date'].strftime('%Y-%m-%d')
                if 'date' in row and pd.notna(row['date'])
                else 'Unknown'
            ),
            'category': str(row.get('category', 'Прочее')),
            'description': str(row.get('description', '')),
            'amount': round(row['amount'], 2) if 'amount' in row else 0.0,
            'currency': str(row.get('currency', 'RUB')),
            'recipient': str(row.get('recipient', 'Неизвестно')),
            'phone': str(row.get('phone', 'Не указан')),
            'transfer_type': str(row.get('transfer_type', 'unknown')),
        }
        results.append(transfer_item)

    return {
        'report_type': 'transfers_to_individuals',
        'client_id': client_id,
        'limit': limit,
        'transfers': results,
    }
