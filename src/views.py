from typing import Any, Dict, Optional
import pandas as pd

from src.utils import logger_utils
from src.reports import (
    generate_report_spending_by_category_json,
    generate_report_spending_by_weekday_json,
    generate_report_spending_by_workday_type_json,
)
from src.services import (
    generate_cashback_json,
    generate_search_by_phone_json,
    generate_search_json,
    generate_transfers_to_individuals_json,
)


def generate_main_page_json(date_time_str: Optional[str] = None) -> Dict[str, Any]:
    if date_time_str is None:
        date_time_str = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")

    logger_utils.debug(
        "generate_main_page_json called", extra={"timestamp": date_time_str}
    )

    cashback = {
        "total": 0.0,
        "currency": "RUB",
        "period": "month",
    }

    investment_bank = {
        "total_balance": 0.0,
        "currency": "RUB",
        "products_count": 0,
    }

    return {
        "timestamp": date_time_str,
        "greeting": "Добрый день!",
        "message": "Виджет аналитики транзакций готов к работе",
        "cashback": cashback,
        "investment_bank": investment_bank,
    }


def generate_events_page_json() -> Dict[str, Any]:
    # Просто возвращаем главную страницу как заглушку, пока нет отдельного события
    return generate_main_page_json()


# Обёртки для остальных сервисов
def generate_search_json_view() -> Dict[str, Any]:
    return generate_search_json(query="")


def generate_search_by_phone_json_view(phone: str) -> Dict[str, Any]:
    return generate_search_by_phone_json(phone)


def generate_transfers_to_individuals_json_view() -> Dict[str, Any]:
    return generate_transfers_to_individuals_json(client_id="")


def generate_report_spending_by_category_json_view(
    client_id: str, days: int = 30
) -> Dict[str, Any]:
    return generate_report_spending_by_category_json(client_id, days=days)


def generate_report_spending_by_weekday_json_view(
    client_id: str, days: int = 30
) -> Dict[str, Any]:
    return generate_report_spending_by_weekday_json(client_id, days=days)


def generate_report_spending_by_workday_type_json_view(
    client_id: str, days: int = 30
) -> Dict[str, Any]:
    return generate_report_spending_by_workday_type_json(client_id, days=days)


def generate_cashback_view(
    client_id: str, currency: str = "RUB", top_n: int = 5
) -> Dict[str, Any]:
    return generate_cashback_json(client_id, currency, top_n)
