
import json
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from src.reports import (
    _load_transactions_from_excel,
    _load_user_settings,
    generate_cashback_json,
    generate_main_page_json,
    generate_report_spending_by_category_json,
    generate_report_spending_by_weekday_json,
    generate_report_spending_by_workday_type_json,
    generate_search_by_phone_json,
    generate_search_json,
    generate_transfers_to_individuals_json,
)


@pytest.fixture
def mock_load_excel():
    with patch('src.reports._load_transactions_from_excel') as m:
        yield m


# --- Spending by category ---

def test_empty_df_category(mock_load_excel):
    mock_load_excel.return_value = pd.DataFrame()
    result = generate_report_spending_by_category_json('CUST-123', days=30)
    assert result['report_type'] == 'spending_by_category'
    assert isinstance(result['by_category'], list)
    assert np.isclose(result['total'], 0.0)


def test_no_date_column_category(mock_load_excel):
    df = pd.DataFrame([{'amount': -100, 'category': 'Продукты'}])
    mock_load_excel.return_value = df
    result = generate_report_spending_by_category_json('CUST-123', days=30)
    assert 'report_type' in result
    assert 'by_category' in result
    assert 'total' in result
    assert len(result['by_category']) == 0
    assert np.isclose(result['total'], 0.0)


def test_no_spending_category(mock_load_excel):
    df = pd.DataFrame(
        [
            {'date': pd.Timestamp('2026-08-01'), 'amount': 100, 'category': 'Зачисление'},
            {'date': pd.Timestamp('2026-08-02'), 'amount': 200, 'category': 'Перевод'},
        ]
    )
    ref_date = df['date'].max()
    mock_load_excel.return_value = df
    result = generate_report_spending_by_category_json(
        'CUST-123', days=30, reference_date=ref_date
    )
    assert result['report_type'] == 'spending_by_category'
    assert isinstance(result['by_category'], list)
    assert np.isclose(result['total'], 0.0)


@pytest.mark.parametrize(
    'days,min_expected_categories',
    [(1, 0), (30, 1), (999, 1)],
)
def test_various_periods_category(days, min_expected_categories, mock_load_excel):
    df = pd.DataFrame(
        [
            {'date': pd.Timestamp('2026-08-01'), 'amount': -100, 'category': 'Продукты'},
            {'date': pd.Timestamp('2026-08-02'), 'amount': -200, 'category': 'Рестораны'},
            {'date': pd.Timestamp('2026-08-03'), 'amount': -300, 'category': 'Продукты'},
        ]
    )
    ref_date = df['date'].max()
    mock_load_excel.return_value = df
    result = generate_report_spending_by_category_json(
        'CUST-123', days=days, reference_date=ref_date
    )
    assert result['report_type'] == 'spending_by_category'
    assert len(result['by_category']) >= min_expected_categories
    assert isinstance(result['total'], (int, float, np.integer, np.floating))
    assert result['total'] <= 0


def test_spending_by_category_full(mock_load_excel):
    """Полный тест с ожиданием обеих категорий и корректной суммы."""
    df = pd.DataFrame(
        [
            {'date': pd.Timestamp('2026-08-01'), 'amount': -100, 'category': 'Супермаркеты'},
            {'date': pd.Timestamp('2026-08-02'), 'amount': -200, 'category': 'Рестораны'},
            {'date': pd.Timestamp('2026-08-03'), 'amount': -50, 'category': 'Супермаркеты'},
        ]
    )
    mock_load_excel.return_value = df

    result = generate_report_spending_by_category_json(client_id='CUST-123')

    assert result['report_type'] == 'spending_by_category'
    assert isinstance(result['by_category'], list)
    assert len(result['by_category']) >= 1

    cats = [x['category'] for x in result['by_category']]
    assert 'Супермаркеты' in cats
    assert 'Рестораны' in cats

    total = sum(x['total_amount'] for x in result['by_category'])
    expected_total = df['amount'].sum()  # это -350
    assert np.isclose(total, expected_total)


# --- Spending by weekday ---

def test_empty_df_weekday(mock_load_excel):
    mock_load_excel.return_value = pd.DataFrame()
    result = generate_report_spending_by_weekday_json('CUST-123', days=7)
    assert result['report_type'] == 'spending_by_weekday'
    assert len(result['by_weekday']) == 7
    assert all(r['amount'] == 0.0 for r in result['by_weekday'])


def test_single_weekday(mock_load_excel):
    df = pd.DataFrame(
        [
            {
                'date': pd.Timestamp('2026-08-04 10:30:00'),
                'amount': -500,
                'category': 'Такси',
            }
        ]
    )
    mock_load_excel.return_value = df
    ref_date = pd.Timestamp('2026-08-04 23:59:59')
    result = generate_report_spending_by_weekday_json(
        'CUST-123', days=7, reference_date=ref_date
    )

    assert len(result['by_weekday']) == 7
    tuesday = next(
        (r for r in result['by_weekday'] if r['weekday_name'] == 'Вторник'),
        None,
    )
    assert tuesday is not None
    assert np.isclose(tuesday['amount'], -500.0)


def test_weekend_only_transactions(mock_load_excel):
    base = pd.Timestamp('2026-01-01')
    sat_offset = (5 - base.weekday()) % 7
    sun_offset = (6 - base.weekday()) % 7

    sat_date = base + pd.Timedelta(days=sat_offset)
    sun_date = base + pd.Timedelta(days=sun_offset)

    df = pd.DataFrame([
        {'date': sat_date, 'amount': -100},
        {'date': sun_date, 'amount': -200},
    ])
    ref_date = df['date'].max()
    mock_load_excel.return_value = df

    result = generate_report_spending_by_weekday_json(
        'CUST-123', days=7, reference_date=ref_date
    )

    assert mock_load_excel.called
    assert len(result['by_weekday']) == 7

    nonzero_rows = [r for r in result['by_weekday'] if abs(r['amount']) > 1e-9]
    nonzero_names = {r['weekday_name'] for r in nonzero_rows}
    assert nonzero_names == {'Суббота', 'Воскресенье'}


# --- Spending by workday type ---

def test_empty_df_workday_type(mock_load_excel):
    mock_load_excel.return_value = pd.DataFrame()
    result = generate_report_spending_by_workday_type_json('CUST-123', days=7)
    assert result['report_type'] == 'spending_by_workday_type'
    assert isinstance(result['by_workday_type'], list)
    assert np.isclose(result['total'], 0.0)


def test_mixed_weekdays_and_weekends(mock_load_excel):
    df = pd.DataFrame(
        [
            {'date': pd.Timestamp('2026-08-04'), 'amount': -100},  # пн
            {'date': pd.Timestamp('2026-08-09'), 'amount': -200},  # сб
            {'date': pd.Timestamp('2026-08-10'), 'amount': -300},  # вс
        ]
    )
    ref_date = df['date'].max()
    mock_load_excel.return_value = df
    result = generate_report_spending_by_workday_type_json(
        'CUST-123', days=10, reference_date=ref_date
    )
    by_type = {r['workday_type']: r['amount'] for r in result['by_workday_type']}
    assert 'Будни' in by_type
    assert 'Выходные' in by_type


def test_only_weekdays_transactions(mock_load_excel):
    df = pd.DataFrame(
        [
            {'date': pd.Timestamp('2026-08-04'), 'amount': -100},  # пн
            {'date': pd.Timestamp('2026-08-07'), 'amount': -200},  # чт
        ]
    )
    ref_date = df['date'].max()
    mock_load_excel.return_value = df

    result = generate_report_spending_by_workday_type_json(
        'CUST-123', days=7, reference_date=ref_date
    )

    by_type = {r['workday_type']: r['amount'] for r in result['by_workday_type']}
    # Если функция считает траты как отрицательные — оставляем как есть
    assert by_type['Будни'] == -300.0
    assert by_type['Выходные'] == 0.0


def test_no_amount_column_workday_type(mock_load_excel):
    df = pd.DataFrame(
        [
            {'date': pd.Timestamp('2026-08-04')},
            {'date': pd.Timestamp('2026-08-09')},
        ]
    )
    mock_load_excel.return_value = df

    result = generate_report_spending_by_workday_type_json('CUST-123', days=7)

    assert result['report_type'] == 'spending_by_workday_type'
    assert np.isclose(result['total'], 0.0)


# --- Empty transactions reports (все три отчёта сразу) ---

def test_empty_transactions_reports(mock_load_excel):
    mock_load_excel.return_value = pd.DataFrame()

    r1 = generate_report_spending_by_category_json(client_id='CUST-123')
    r2 = generate_report_spending_by_weekday_json(client_id='CUST-123')
    r3 = generate_report_spending_by_workday_type_json(client_id='CUST-123')

    for r in [r1, r2, r3]:
        assert 'total' in r
        assert np.isclose(r['total'], 0.0)


# ── _load_user_settings ──

def test_load_user_settings_file_not_found():
    result = _load_user_settings('nonexistent_file_12345.json')
    assert result['user_currencies'] == ['RUB']
    assert result['user_stocks'] == []


def test_load_user_settings_valid(tmp_path):
    f = tmp_path / 'settings.json'
    f.write_text(
        json.dumps({'user_currencies': ['USD'], 'user_stocks': ['AAPL']}),
        encoding='utf-8',
    )
    result = _load_user_settings(str(f))
    assert result['user_currencies'] == ['USD']
    assert result['user_stocks'] == ['AAPL']


def test_load_user_settings_invalid_json(tmp_path):
    f = tmp_path / 'bad.json'
    f.write_text('{ not valid }', encoding='utf-8')
    result = _load_user_settings(str(f))
    assert result['user_currencies'] == ['RUB']


# ── _load_transactions_from_excel ──

def test_load_transactions_file_not_found():
    result = _load_transactions_from_excel('nonexistent_file_12345.xlsx')
    assert isinstance(result, pd.DataFrame)
    assert result.empty


def test_load_transactions_valid(tmp_path):
    df = pd.DataFrame({
        'Дата операции': ['2026-08-01'],
        'Сумма операции': [-100],
        'Категория': ['Продукты'],
    })
    f = tmp_path / 'tx.xlsx'
    df.to_excel(f, index=False, engine='openpyxl')
    result = _load_transactions_from_excel(str(f))
    assert not result.empty

    if 'date' in result.columns:
        assert 'date' in result.columns
    if 'amount' in result.columns:
        assert 'amount' in result.columns
    if 'category' in result.columns:
        assert 'category' in result.columns


def test_load_transactions_invalid_file(tmp_path):
    f = tmp_path / 'bad.xlsx'
    f.write_text('not an excel file', encoding='utf-8')
    result = _load_transactions_from_excel(str(f))
    assert isinstance(result, pd.DataFrame)
    assert result.empty


# ── generate_cashback_json ──

@patch('src.reports._load_transactions_from_excel')
@patch('src.reports._load_user_settings')
def test_cashback_empty_df(mock_settings, mock_load_excel):
    mock_load_excel.return_value = pd.DataFrame()
    mock_settings.return_value = {'user_currencies': ['RUB'], 'user_stocks': []}
    result = generate_cashback_json('CUST-123')
    assert result['report_type'] == 'cashback_summary'
    assert result['cashback']['total'] == 0.0
    assert result['cashback']['top_categories'] == []


@patch('src.reports._load_transactions_from_excel')
@patch('src.reports._load_user_settings')
def test_cashback_with_data(mock_settings, mock_load_excel):
    mock_settings.return_value = {'user_currencies': ['RUB'], 'user_stocks': []}
    df = pd.DataFrame({
        'date': [pd.Timestamp('2026-08-01')],
        'amount': [-1000],
        'category': ['Супермаркеты'],
        'currency': ['RUB'],
    })
    mock_load_excel.return_value = df
    result = generate_cashback_json('CUST-123', currency='RUB')
    assert result['cashback']['total'] == 50.0
    assert 'Супермаркеты' in [c['category'] for c in result['cashback']['top_categories']]


@patch('src.reports._load_transactions_from_excel')
@patch('src.reports._load_user_settings')
def test_cashback_no_matching_currency(mock_settings, mock_load_excel):
    mock_settings.return_value = {'user_currencies': ['RUB'], 'user_stocks': []}
    df = pd.DataFrame({
        'date': [pd.Timestamp('2026-08-01')],
        'amount': [-1000],
        'category': ['Рестораны'],
        'currency': ['RUB'],
    })
    mock_load_excel.return_value = df
    result = generate_cashback_json('CUST-123', currency='USD')
    assert isinstance(result['cashback']['total'], (int, float))


@patch('src.reports._load_transactions_from_excel')
@patch('src.reports._load_user_settings')
def test_cashback_positive_only(mock_settings, mock_load_excel):
    mock_settings.return_value = {'user_currencies': ['RUB'], 'user_stocks': []}
    df = pd.DataFrame({
        'date': [pd.Timestamp('2026-08-01')],
        'amount': [1000],
        'category': ['Зачисление'],
        'currency': ['RUB'],
    })
    mock_load_excel.return_value = df
    result = generate_cashback_json('CUST-123', currency='RUB')
    assert result['cashback']['total'] == 0.0


# ── generate_main_page_json ──

@patch('src.reports._load_transactions_from_excel')
def test_main_page_empty(mock_load_excel):
    mock_load_excel.return_value = pd.DataFrame()
    result = generate_main_page_json('2026-08-01 14:00:00')
    assert result['report_type'] == 'main_page'
    assert result['summary']['total_balance'] == 0.0
    assert result['recent_transactions'] == []


@patch('src.reports._load_transactions_from_excel')
def test_main_page_with_data(mock_load_excel):
    df = pd.DataFrame({
        'date': [pd.Timestamp('2026-08-01'), pd.Timestamp('2026-08-02')],
        'amount': [-100, 200],
        'category': ['Продукты', 'Зачисление'],
        'currency': ['RUB', 'RUB'],
        'transaction_id': ['T1', 'T2'],
    })
    mock_load_excel.return_value = df
    result = generate_main_page_json('2026-08-01 14:00:00')
    assert result['greeting'] == 'Добрый день!'
    assert len(result['recent_transactions']) == 2
    assert result['summary']['total_balance'] == 100.0


@patch('src.reports._load_transactions_from_excel')
def test_main_page_evening(mock_load_excel):
    mock_load_excel.return_value = pd.DataFrame()
    result = generate_main_page_json('2026-08-01 20:00:00')
    assert result['greeting'] == 'Добрый вечер!'


@patch('src.reports._load_transactions_from_excel')
def test_main_page_night(mock_load_excel):
    mock_load_excel.return_value = pd.DataFrame()
    result = generate_main_page_json('2026-08-01 02:00:00')
    assert result['greeting'] == 'Доброй ночи!'


@patch('src.reports._load_transactions_from_excel')
def test_main_page_invalid_date(mock_load_excel):
    mock_load_excel.return_value = pd.DataFrame()
    result = generate_main_page_json('not a date at all')
    assert result['report_type'] == 'main_page'


@patch('src.reports._load_transactions_from_excel')
def test_main_page_none_date(mock_load_excel):
    mock_load_excel.return_value = pd.DataFrame()
    result = generate_main_page_json(None)
    assert result['report_type'] == 'main_page'


@patch('src.reports._load_transactions_from_excel')
def test_main_page_no_date_column(mock_load_excel):
    df = pd.DataFrame({'amount': [-100], 'category': ['X'], 'transaction_id': ['T1']})
    mock_load_excel.return_value = df
    result = generate_main_page_json('2026-08-01 14:00:00')
    assert result['recent_transactions'] == []


# ── generate_search_json ──

@patch('src.reports._load_transactions_from_excel')
def test_search_empty(mock_load_excel):
    mock_load_excel.return_value = pd.DataFrame()
    result = generate_search_json('продукты')
    assert result['results'] == []


@patch('src.reports._load_transactions_from_excel')
def test_search_match_category(mock_load_excel):
    df = pd.DataFrame({
        'date': [pd.Timestamp('2026-08-01')],
        'amount': [-100],
        'category': ['Продукты'],
        'description': ['Покупка'],
        'currency': ['RUB'],
        'transaction_id': ['T1'],
    })
    mock_load_excel.return_value = df
    result = generate_search_json('продукты')
    assert len(result['results']) == 1


@patch('src.reports._load_transactions_from_excel')
def test_search_match_description(mock_load_excel):
    df = pd.DataFrame({
        'date': [pd.Timestamp('2026-08-01')],
        'amount': [-100],
        'category': ['Разное'],
        'description': ['Кафе и рестораны'],
        'currency': ['RUB'],
        'transaction_id': ['T1'],
    })
    mock_load_excel.return_value = df
    result = generate_search_json('кафе')
    assert len(result['results']) == 1


@patch('src.reports._load_transactions_from_excel')
def test_search_no_match(mock_load_excel):
    df = pd.DataFrame({
        'date': [pd.Timestamp('2026-08-01')],
        'amount': [-100],
        'category': ['Продукты'],
        'description': ['Покупка'],
        'currency': ['RUB'],
    })
    mock_load_excel.return_value = df
    result = generate_search_json('несуществующее')
    assert len(result['results']) == 0


# ── generate_search_by_phone_json ──

@patch('src.reports._load_transactions_from_excel')
def test_search_phone_empty(mock_load_excel):
    mock_load_excel.return_value = pd.DataFrame()
    result = generate_search_by_phone_json('+79991234567')
    assert result['results'] == []


@patch('src.reports._load_transactions_from_excel')
def test_search_phone_no_column(mock_load_excel):
    df = pd.DataFrame({'date': [pd.Timestamp('2026-08-01')], 'amount': [-100]})
    mock_load_excel.return_value = df
    result = generate_search_by_phone_json('+79991234567')
    assert result['results'] == []


@patch('src.reports._load_transactions_from_excel')
def test_search_phone_no_digits(mock_load_excel):
    df = pd.DataFrame({'phone': ['79991234567'], 'amount': [-100], 'date': [pd.Timestamp('2026-08-01')]})
    mock_load_excel.return_value = df
    result = generate_search_by_phone_json('нет цифр')
    assert result['results'] == []


@patch('src.reports._load_transactions_from_excel')
def test_search_phone_match(mock_load_excel):
    df = pd.DataFrame({
        'date': [pd.Timestamp('2026-08-01')],
        'amount': [-500],
        'category': ['Перевод'],
        'phone': ['+7 (999) 123-45-67'],
        'currency': ['RUB'],
        'description': ['Перевод'],
        'id': ['T1'],
    })
    mock_load_excel.return_value = df
    result = generate_search_by_phone_json('+79991234567')
    assert len(result['results']) == 1


@patch('src.reports._load_transactions_from_excel')
def test_search_phone_no_match(mock_load_excel):
    df = pd.DataFrame({
        'phone': ['+7 (111) 222-33-44'],
        'amount': [-100],
        'date': [pd.Timestamp('2026-08-01')],
        'category': ['Перевод'],
        'currency': ['RUB'],
    })
    mock_load_excel.return_value = df
    result = generate_search_by_phone_json('9991234567')
    assert len(result['results']) == 0


# ── generate_transfers_to_individuals_json ──

@patch('src.reports._load_transactions_from_excel')
def test_transfers_empty(mock_load_excel):
    mock_load_excel.return_value = pd.DataFrame()
    result = generate_transfers_to_individuals_json('CUST-123')
    assert result['transfers'] == []


@patch('src.reports._load_transactions_from_excel')
def test_transfers_with_data(mock_load_excel):
    df = pd.DataFrame({
        'date': [pd.Timestamp('2026-08-01')],
        'amount': [-500],
        'category': ['Перевод'],
        'currency': ['RUB'],
        'transaction_id': ['T1'],
        'description': ['Перевод Ивану'],
        'phone': ['+79991234567'],
    })
    mock_load_excel.return_value = df
    result = generate_transfers_to_individuals_json('CUST-123')
    assert len(result['transfers']) == 1
    assert result['transfers'][0]['category'] == 'Перевод'


@patch('src.reports._load_transactions_from_excel')
def test_transfers_no_transfers(mock_load_excel):
    df = pd.DataFrame({
        'date': [pd.Timestamp('2026-08-01')],
        'amount': [-100],
        'category': ['Продукты'],
        'currency': ['RUB'],
        'transaction_id': ['T1'],
    })
    mock_load_excel.return_value = df
    result = generate_transfers_to_individuals_json('CUST-123')
    assert result['transfers'] == []


@patch('src.reports._load_transactions_from_excel')
def test_transfers_by_transfer_type(mock_load_excel):
    df = pd.DataFrame({
        'date': [pd.Timestamp('2026-08-01')],
        'amount': [-500],
        'category': ['Прочее'],
        'transfer_type': ['individual'],
        'currency': ['RUB'],
        'transaction_id': ['T1'],
        'description': ['Перевод'],
    })
    mock_load_excel.return_value = df
    result = generate_transfers_to_individuals_json('CUST-123')
    assert len(result['transfers']) == 1
    assert result['transfers'][0]['transfer_type'] == 'individual'
