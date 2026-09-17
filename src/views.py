from typing import Any, Dict, Optional

from src.utils import (
    get_cards_info,
    get_currency_rates,
    get_greeting,
    get_stock_prices,
    get_top_transactions,
    load_transactions,
    logger_utils,
)


def generate_main_page_json(
    date_time_str: Optional[str] = None,
    transactions_file: str = 'data/operations.xlsx',
    settings_file: str = 'data/user_settings.json',
) -> Dict[str, Any]:
    """Генерирует JSON для главной страницы с реальными данными."""
    logger_utils.info('Генерация главной страницы')

    greeting = get_greeting(date_time_str)
    df = load_transactions(transactions_file)

    cards = get_cards_info(df)
    top_transactions = get_top_transactions(df, n=5)
    currency_rates = get_currency_rates(settings_file)
    stock_prices = get_stock_prices(settings_file)

    return {
        'greeting': greeting,
        'cards': cards,
        'top_transactions': top_transactions,
        'currency_rates': currency_rates,
        'stock_prices': stock_prices,
    }
