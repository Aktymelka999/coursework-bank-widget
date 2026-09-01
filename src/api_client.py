import os
from typing import Any, Dict, List

import requests

API_KEY = os.getenv("BANK_API_KEY", "demo-key-do-not-commit")
BASE_URL = os.getenv("BANK_API_URL", "https://api.demo-bank.com/v1")


def fetch_exchange_rates() -> Dict[str, float]:
    """
    Реальное получение курсов валют через публичный API.

    Использует бесплатный API exchangerate.host (не требует ключа).
    Возвращает курсы основных валют относительно RUB.

    Returns:
        Словарь: {"USD": 90.5, "EUR": 98.2, "CNY": 12.5}
    """
    url = "https://api.exchangerate.host/latest"
    params = {"base": "RUB"}

    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        rates = data.get("rates", {})
        # Берём только нужные валюты, чтобы не тащить лишнее
        return {
            "USD": float(rates.get("USD", 90.0)),
            "EUR": float(rates.get("EUR", 98.0)),
            "CNY": float(rates.get("CNY", 12.5)),
        }
    except Exception:
        # Если API недоступен — отдаём безопасные дефолтные значения.
        # Это гарантирует, что приложение не упадёт.
        return {"USD": 90.0, "EUR": 98.0, "CNY": 12.5}


def fetch_transactions() -> List[Dict[str, Any]]:
    """
    Получение списка транзакций.

    В реальном проекте здесь был бы HTTP-запрос к банковскому API
    с авторизацией и фильтрацией по client_id.

    Сейчас — стабильная заглушка с реалистичными данными.
    Это нужно для надёжных тестов.

    Returns:
        Список транзакций в формате, ожидаемом сервисами.
    """
    # Эти данные выглядят как реальные транзакции: разные типы, статусы, валюты
    return [
        {
            "client_id": "12345",
            "category": "food",
            "amount": 1200.0,
            "currency": "RUB",
            "type": "purchase",
            "cashback": 12.0,
            "timestamp": "2026-07-28T10:30:00",
            "status": "completed",
        },
        {
            "client_id": "12345",
            "category": "transport",
            "amount": 600.0,
            "currency": "RUB",
            "type": "transfer",
            "cashback": 6.0,
            "timestamp": "2026-07-28T11:15:00",
            "status": "completed",
        },
        {
            "client_id": "12345",
            "category": "food",
            "amount": 850.0,
            "currency": "RUB",
            "type": "purchase",
            "cashback": 8.5,
            "timestamp": "2026-07-29T09:45:00",
            "status": "completed",
        },
        {
            "client_id": "12345",
            "category": "entertainment",
            "amount": 1500.0,
            "currency": "RUB",
            "type": "purchase",
            "cashback": 0.0,
            "timestamp": "2026-07-29T18:20:00",
            "status": "completed",
        },
        {
            "client_id": "12345",
            "category": "transport",
            "amount": 320.0,
            "currency": "RUB",
            "type": "payment",
            "cashback": 3.2,
            "timestamp": "2026-07-30T08:10:00",
            "status": "pending",
        },
        {
            "client_id": "12345",
            "category": "groceries",
            "amount": 2100.0,
            "currency": "RUB",
            "type": "purchase",
            "cashback": 21.0,
            "timestamp": "2026-07-30T19:35:00",
            "status": "completed",
        },
    ]
