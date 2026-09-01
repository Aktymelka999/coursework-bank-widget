import pytest
import requests
from unittest.mock import patch, MagicMock

from src.api_client import fetch_exchange_rates, fetch_transactions


class TestAPIClientFunctions:
    @patch("src.api_client.requests.get")
    def test_fetch_exchange_rates_success(self, mock_get):
        # Подготавливаем успешный ответ
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "base": "RUB",
            "rates": {
                "USD": 91.0,
                "EUR": 99.0,
                "CNY": 12.8,
                # добавим лишние валюты, чтобы проверить фильтрацию
                "JPY": 0.6,
            },
        }
        mock_get.return_value = mock_response

        result = fetch_exchange_rates()

        # Проверяем, что запрос ушёл
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert "https://api.exchangerate.host/latest" in args[0]
        assert kwargs["params"] == {"base": "RUB"}

        # Проверяем, что вернулись только нужные валюты и в float
        assert isinstance(result, dict)
        assert set(result.keys()) == {"USD", "EUR", "CNY"}
        assert result["USD"] == 91.0
        assert result["EUR"] == 99.0
        assert result["CNY"] == 12.8

    @patch("src.api_client.requests.get", side_effect=requests.exceptions.RequestException("Network error"))
    def test_fetch_exchange_rates_fallback_on_error(self, mock_get):
        result = fetch_exchange_rates()

        # При ошибке API функция должна вернуть безопасные дефолты
        assert result == {"USD": 90.0, "EUR": 98.0, "CNY": 12.5}
        mock_get.assert_called_once()

    @patch("src.api_client.requests.get", side_effect=Exception("Unexpected error"))
    def test_fetch_exchange_rates_fallback_on_any_exception(self, mock_get):
        result = fetch_exchange_rates()
        assert result == {"USD": 90.0, "EUR": 98.0, "CNY": 12.5}

    def test_fetch_transactions_returns_valid_structure(self):
        """
        fetch_transactions сейчас — заглушка, поэтому мы не мокаем requests,
        а проверяем, что возвращается корректный список словарей с нужными полями.
        """
        result = fetch_transactions()

        assert isinstance(result, list)
        assert len(result) == 6

        first = result[0]
        required_keys = {
            "client_id", "category", "amount", "currency",
            "type", "cashback", "timestamp", "status"
        }
        assert required_keys.issubset(first.keys())

        # Проверим типы некоторых полей
        assert isinstance(first["amount"], (int, float))
        assert isinstance(first["cashback"], (int, float))
        assert isinstance(first["timestamp"], str)
        assert first["status"] in ("completed", "pending")