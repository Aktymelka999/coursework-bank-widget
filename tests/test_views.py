
from src.views import generate_main_page_json


def test_generate_main_page_json_basic():
    data = generate_main_page_json()

    assert isinstance(data, dict)

    assert 'timestamp' in data
    assert 'greeting' in data
    assert 'message' in data
    assert 'cashback' in data
    assert 'investment_bank' in data

    cashback = data['cashback']
    assert 'total' in cashback
    assert 'currency' in cashback
    assert 'period' in cashback

    investment = data['investment_bank']
    assert 'total_balance' in investment
    assert 'currency' in investment
    assert 'products_count' in investment
