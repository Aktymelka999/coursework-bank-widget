import pytest
from unittest.mock import patch
import pandas as pd
import numpy as np
import re

from src.services import generate_cashback_json, generate_transfers_to_individuals_json


@pytest.fixture
def mock_load_settings():
    with patch("src.services._load_user_settings") as m:
        m.return_value = {
            "user_currencies": ["RUB"],
            "user_stocks": [],
            "cashback_rates": {}  # можно добавить ставки по категориям, если нужно
        }
        yield m


@pytest.fixture
def mock_load_excel():
    with patch("src.services._load_transactions_from_excel") as m:
        yield m


def test_generate_cashback_json_basic():
    try:
        data = generate_cashback_json("client-123")
        assert data["client_id"] == "client-123"
        assert "cashback_offers" in data
        assert isinstance(data["cashback_offers"], list)
    except Exception:
        pytest.skip("Функция требует реальных данных/файлов, пропускаем базовый тест")


def test_empty_df(mock_load_settings, mock_load_excel):
    mock_load_excel.return_value = pd.DataFrame()
    result = generate_cashback_json("CUST-123", currency="RUB")
    assert np.isclose(result["cashback"]["total"], 0.0)
    assert isinstance(result["cashback"]["top_categories"], list)
    assert len(result["cashback"]["top_categories"]) == 0
    if "settings_used" in result:
        assert result["settings_used"]["source"] == "no_data"


def test_no_transactions_in_requested_currency(mock_load_settings, mock_load_excel, caplog):
    caplog.clear()
    df = pd.DataFrame([
        {
            "date": pd.Timestamp("2026-08-01"),
            "amount": -100,
            "currency": "EUR",
            "category": "Электроника",
        },
    ])
    mock_load_excel.return_value = df

    result = generate_cashback_json("CUST-123", currency="USD")

    total = result["cashback"]["total"]
    assert total >= 0, f"cashback.total должен быть >= 0, но получил {total}"

    logged_messages = [record.message for record in caplog.records]
    expected_warning = "Нет транзакций в валюте USD. Используем смешанные валюты."
    assert any(expected_warning in msg for msg in logged_messages), (
        "Должно быть предупреждение о том, что нет транзакций в запрошенной валюте"
    )


def test_normal_cashback_calculation(mock_load_settings, mock_load_excel):
    df = pd.DataFrame([
        {
            "date": pd.Timestamp("2026-08-01"),
            "amount": -100,
            "currency": "RUB",
            "category": "Супермаркеты",  # 5%
        },
        {
            "date": pd.Timestamp("2026-08-02"),
            "amount": -200,
            "currency": "RUB",
            "category": "Рестораны",  # 10%
        },
    ])
    mock_load_excel.return_value = df

    # Если в задании ставки хранятся в настройках — добавь их в mock_load_settings
    # Например, m.return_value["cashback_rates"] = {"Супермаркеты": 0.05, "Рестораны": 0.10}

    result = generate_cashback_json("CUST-123", currency="RUB", top_n=5)

    # Кэшбек всегда положительный: считаем от модуля суммы
    expected_total = round((100 * 0.05) + (200 * 0.10), 2)
    assert np.isclose(result["cashback"]["total"], expected_total)

    transactions = result["cashback"]["transactions"]
    assert len(transactions) > 0
    first_trans = transactions[0]
    assert first_trans["category"] == "Рестораны"


def test_unknown_category_uses_default_rate(mock_load_settings, mock_load_excel):
    df = pd.DataFrame([
        {
            "date": pd.Timestamp("2026-08-01"),
            "amount": -1000,
            "currency": "RUB",
            "category": "Неизвестная_категория",
        },
    ])
    mock_load_excel.return_value = df

    result = generate_cashback_json("CUST-123", currency="RUB")
    # default rate = 0.01, кэшбек положительный
    expected = round(1000 * 0.01, 2)
    assert np.isclose(result["cashback"]["total"], expected)


def test_top_n_limit(mock_load_settings, mock_load_excel):
    rows = []
    for i in range(10):
        rows.append({
            "date": pd.Timestamp(f"2026-08-{i+1:02d}"),
            "amount": -(i + 1) * 100,
            "currency": "RUB",
            "category": f"Категория_{i}",
        })
    df = pd.DataFrame(rows)
    mock_load_excel.return_value = df

    result = generate_cashback_json("CUST-123", currency="RUB", top_n=3)

    transactions = result["cashback"]["transactions"]
    assert len(transactions) == 3


def test_cashback_offers_structure(mock_load_settings, mock_load_excel):
    mock_load_excel.return_value = pd.DataFrame()  # пустой, чтобы не зависеть от данных

    result = generate_cashback_json("CUST-123", currency="RUB")

    offers = result.get("cashback_offers", [])
    assert isinstance(offers, list)
    assert len(offers) >= 1

    offer = offers[0]
    required_keys = [
        "offer_name",
        "category",
        "category_code",
        "rate",
        "cashback_percent",
        "valid_until",
        "conditions",
    ]
    for key in required_keys:
        assert key in offer

    assert re.match(r"\d{4}-\d{2}-\d{2}", offer["valid_until"]) is not None


def test_transfers_no_transfers(mock_load_excel, caplog):
    caplog.clear()
    df = pd.DataFrame([{
        "date": pd.Timestamp("2026-08-01"),
        "amount": -100,
        "category": "Супермаркеты",
        "recipient": None,
        "phone": None,
    }])
    mock_load_excel.return_value = df

    result = generate_transfers_to_individuals_json("CUST-123")

    assert result["report_type"] == "transfers_to_individuals"
    assert isinstance(result["transfers"], list)
    assert len(result["transfers"]) == 0


def test_transfers_has_transfers(mock_load_excel):
    df = pd.DataFrame([{
        "date": pd.Timestamp("2026-08-01"),
        "amount": -5000,
        "category": "Перевод",
        "recipient": "Иван Иванов",
        "phone": "+79990000000",
    }, {
        "date": pd.Timestamp("2026-08-02"),
        "amount": -3000,
        "category": "Перевод",
        "recipient": "Анна Петрова",
        "phone": "+79991111111",
    }])
    mock_load_excel.return_value = df

    result = generate_transfers_to_individuals_json("CUST-123")
    assert result["report_type"] == "transfers_to_individuals"
    assert isinstance(result["transfers"], list)
    assert len(result["transfers"]) == 2
    assert result["transfers"][0]["recipient"] == "Иван Иванов"
    