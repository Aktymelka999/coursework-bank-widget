

from src.services import calculate_investment_bank


def test_investment_rounding_up():
    """Проверяет, что округление идёт вверх до шага и в копилку уходит ровно step."""
    original_amount = 1051
    step = 50
    result = calculate_investment_bank(original_amount, step)

    assert result["original_amount"] == original_amount
    
    assert result["rounded_amount"] == 1100
    
    assert result["investment_amount"] == step


def test_investment_exact_multiple():
    """Проверяет случай, когда сумма кратна шагу."""
    original_amount = 1000
    step = 50
    result = calculate_investment_bank(original_amount, step)
    
    assert result["rounded_amount"] == 1000
    assert result["investment_amount"] == 0 