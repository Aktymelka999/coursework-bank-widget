import math
from typing import List, Dict, Any
import pandas as pd


def get_currency_rates(currencies: List[str]) -> Dict[str, float]:
    """
    Возвращает курсы валют.
    Сейчас это заглушки для теста. Позже сюда можно вставить запрос к API ЦБ или брокеру.
    """

    mock_rates = {"USD": 90.0, "EUR": 98.0}
    result = {}
    for curr in currencies:
        result[curr] = mock_rates.get(curr, 85.0)
    return result


def get_stock_prices(stocks: List[str]) -> Dict[str, float]:
    """
    Возвращает цены акций.
    Сейчас это заглушки для теста.
    """

    mock_prices = {
        "AAPL": 185.5,
        "AMZN": 135.2,
        "GOOGL": 140.0,
        "MSFT": 380.1,
        "TSLA": 250.0,
    }
    result = {}
    for stock in stocks:
        result[stock] = mock_prices.get(stock, 100.0)
    return result


def filter_by_range(
    df: pd.DataFrame, date_str: str, range_type: str = "M"
) -> pd.DataFrame:
    """Фильтрует DataFrame по диапазону дат."""
    if "Дата операции" not in df.columns:
        return df

    target_date = pd.to_datetime(date_str)

    if range_type == "ALL":
        return df[df["Дата операции"] <= target_date]

    if range_type == "Y":
        start_date = target_date.replace(month=1, day=1)
        return df[
            (df["Дата операции"] >= start_date) & (df["Дата операции"] <= target_date)
        ]

    if range_type == "W":

        start_date = target_date - pd.Timedelta(days=target_date.weekday())
        start_date = start_date.replace(hour=0, minute=0, second=0)
        return df[
            (df["Дата операции"] >= start_date) & (df["Дата операции"] <= target_date)
        ]

    start_date = target_date.replace(day=1)
    return df[
        (df["Дата операции"] >= start_date) & (df["Дата операции"] <= target_date)
    ]


def calculate_expenses_and_income(df: pd.DataFrame) -> Dict[str, Any]:
    """Считает расходы и поступления, группирует категории."""
    data = df.copy()

    if not pd.api.types.is_numeric_dtype(data["Сумма платежа"]):
        data["Сумма платежа"] = pd.to_numeric(
            data["Сумма платежа"], errors="coerce"
        ).fillna(0)

    income_keywords = ["пополнение", "проценты", "кэшбэк"]

    expenses_df = data[
        ~data["Категория"].str.lower().str.contains("|".join(income_keywords), na=False)
    ]
    income_df = data[
        data["Категория"].str.lower().str.contains("|".join(income_keywords), na=False)
    ]

    total_expenses = expenses_df["Сумма платежа"].sum()
    total_income = income_df["Сумма платежа"].sum()

    # --- РАСХОДЫ: Топ-7 категорий + Остальное ---
    exp_grouped = expenses_df.groupby("Категория")["Сумма платежа"].sum().reset_index()
    exp_grouped = exp_grouped.sort_values(by="Сумма платежа", ascending=False)

    top_7 = exp_grouped.head(7)
    rest_sum = exp_grouped.iloc[7:]["Сумма платежа"].sum()

    main_expenses = []
    for _, row in top_7.iterrows():
        main_expenses.append(
            {"category": row["Категория"], "amount": int(round(row["Сумма платежа"]))}
        )

    if rest_sum > 0:
        main_expenses.append({"category": "Остальное", "amount": int(round(rest_sum))})

    # --- РАСХОДЫ: Переводы и наличные ---
    transfers_and_cash = []
    for cat in ["Наличные", "Переводы"]:
        cat_df = expenses_df[expenses_df["Категория"] == cat]
        if not cat_df.empty:
            amount = cat_df["Сумма платежа"].sum()
            if amount > 0:
                transfers_and_cash.append(
                    {"category": cat, "amount": int(round(amount))}
                )

    # --- ПОСТУПЛЕНИЯ: Топ категорий ---
    inc_grouped = income_df.groupby("Категория")["Сумма платежа"].sum().reset_index()
    inc_grouped = inc_grouped.sort_values(by="Сумма платежа", ascending=False)

    main_income = []
    for _, row in inc_grouped.iterrows():
        main_income.append(
            {"category": row["Категория"], "amount": int(round(row["Сумма платежа"]))}
        )

    return {
        "expenses": {
            "total_amount": int(round(total_expenses)),
            "main": main_expenses,
            "transfers_and_cash": transfers_and_cash,
        },
        "income": {"total_amount": int(round(total_income)), "main": main_income},
    }


def calculate_round_up(amount: float, step: int) -> float:
    """
    Округляет сумму вверх до ближайшего кратного step.
    Пример: amount=1051, step=50 -> вернет 1100.
    """
    if step <= 0:
        return amount
    return math.ceil(amount / step) * step


def calculate_investment_bank(original_amount: int, step: int) -> dict:
    """
    Округляет сумму вверх до ближайшего кратного step.
    В копилку идёт step только если есть «остаток» (т.е. сумма не кратна шагу).
    Если сумма уже кратна шагу — в копилку 0.
    """
    rounded_amount = math.ceil(original_amount / step) * step

    if rounded_amount == original_amount:
        investment_amount = 0
    else:

        investment_amount = step

    return {
        "original_amount": original_amount,
        "rounded_amount": rounded_amount,
        "investment_amount": investment_amount,
    }


def search_transactions(df: pd.DataFrame, query: str) -> List[Dict[str, Any]]:
    """
    Ищет транзакции по подстроке (нечувствителен к регистру).
    Ищет в полях: 'Категория' и 'Описание'.
    """
    if not query or not isinstance(query, str):
        return []

    q = query.lower()

    mask_category = df["Категория"].astype(str).str.lower().str.contains(q, na=False)
    mask_description = df["Описание"].astype(str).str.lower().str.contains(q, na=False)

    filtered_df = df[mask_category | mask_description]

    results = []
    for _, row in filtered_df.iterrows():
        date_str = (
            row["Дата операции"].strftime("%d.%m.%Y")
            if pd.notna(row["Дата операции"])
            else "Неизвестна"
        )
        results.append(
            {
                "date": date_str,
                "amount": round(row["Сумма платежа"], 2),
                "category": row["Категория"],
                "description": row["Описание"],
            }
        )
    return results


def get_top_5_transactions(df: pd.DataFrame) -> List[Dict[str, Any]]:
    if df.empty:
        return []

    top_5 = df.head(5)
    results = []
    for _, row in top_5.iterrows():
        date_str = (
            row["Дата операции"].strftime("%d.%m.%Y")
            if pd.notna(row["Дата операции"])
            else "Неизвестна"
        )
        results.append(
            {
                "date": date_str,
                "amount": round(row["Сумма платежа"], 2),
                "category": row["Категория"],
                "description": row["Описание"],
            }
        )
    return results


def calculate_cards_stats(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Считает статистику по картам: общая сумма, количество транзакций, средняя сумма.
    Возвращает список словарей: по одному на каждую карту.
    """
    if df.empty:
        return []

    card_col = "Карта"
    if card_col not in df.columns:

        if "Card" in df.columns:
            card_col = "Card"
        else:

            return []

    grouped = (
        df.groupby(card_col)
        .agg(
            total_amount=("Сумма платежа", "sum"),
            transaction_count=("Сумма платежа", "count"),
            avg_amount=("Сумма платежа", "mean"),
        )
        .reset_index()
    )

    results = []
    for _, row in grouped.iterrows():
        results.append(
            {
                "card_name": row[card_col],
                "total_amount": round(row["total_amount"], 2),
                "transaction_count": int(row["transaction_count"]),
                "avg_amount": round(row["avg_amount"], 2),
            }
        )

    return results


def get_high_cashback_categories() -> list[dict]:
    """
    Возвращает список категорий с повышенным кешбэком.
    Это можно позже заменить на чтение из конфига или БД.
    """
    return [
        {"category": "Продукты", "cashback_percent": 5.0},
        {"category": "Такси", "cashback_percent": 7.0},
        {"category": "Электроника", "cashback_percent": 3.0},
        {"category": "Рестораны", "cashback_percent": 6.0},
    ]


def search_by_phone(df: pd.DataFrame, phone_query: str) -> list[dict]:
    """
    Ищет транзакции, где в описании встречается фрагмент запроса.
    Регистронезависимо. Всегда возвращает список (может быть пустым).
    """
    # Защита от некорректных входных данных
    if df is None or df.empty or not phone_query or not isinstance(phone_query, str):
        return []

    q = phone_query.lower()

    if "Описание" not in df.columns:
        return []

    masked_col = df["Описание"].astype(str).str.lower()

    filtered = df[masked_col.str.contains(q, na=False)]

    results = []
    for _, row in filtered.iterrows():
        date_val = row["Дата операции"]
        if pd.notna(date_val):
            date_str = date_val.strftime("%d.%m.%Y")
        else:
            date_str = "Неизвестна"

        results.append(
            {
                "date": date_str,
                "amount": (
                    round(float(row["Сумма платежа"]), 2)
                    if pd.notna(row["Сумма платежа"])
                    else 0.0
                ),
                "category": (
                    str(row["Категория"])
                    if pd.notna(row["Категория"])
                    else "Без категории"
                ),
                "description": (
                    str(row["Описание"]) if pd.notna(row["Описание"]) else ""
                ),
            }
        )

    return results


def search_transfers_to_individuals(df: pd.DataFrame) -> list[dict]:
    """
    Находит переводы физическим лицам: категория 'Переводы'
    и в описании есть упоминание 'физ. лицу' или 'физическому лицу'.
    """
    if df.empty:
        return []

    desc_lower = df["Описание"].astype(str).str.lower()
    is_transfer = (
        df["Категория"].astype(str).str.lower().str.contains("переводы", na=False)
    )

    has_individual = desc_lower.str.contains(
        "физ. лицу|физическому лицу", na=False, regex=True
    )

    filtered = df[is_transfer & has_individual]

    results = []
    for _, row in filtered.iterrows():
        date_str = (
            row["Дата операции"].strftime("%d.%m.%Y")
            if pd.notna(row["Дата операции"])
            else "Неизвестна"
        )
        results.append(
            {
                "date": date_str,
                "amount": round(row["Сумма платежа"], 2),
                "category": row["Категория"],
                "description": row["Описание"],
            }
        )
    return results


def report_spending_by_category(df: pd.DataFrame) -> list[dict]:
    if df.empty:
        return []

    income_keywords = ["пополнение", "проценты", "кэшбэк"]
    expenses = df[
        ~df["Категория"].str.lower().str.contains("|".join(income_keywords), na=False)
    ]

    grouped = (
        expenses.groupby("Категория", dropna=False)["Сумма платежа"].sum().reset_index()
    )
    grouped = grouped.sort_values("Сумма платежа", ascending=False)

    result = []
    for _, row in grouped.iterrows():
        cat = row["Категория"] if pd.notna(row["Категория"]) else "Без категории"
        result.append(
            {
                "category": cat,
                "total_amount": round(float(row["Сумма платежа"]), 2),
            }
        )
    return result


def report_spending_by_weekday(df: pd.DataFrame) -> list[dict]:
    if df.empty:
        return []

    income_keywords = ["пополнение", "проценты", "кэшбэк"]
    expenses = df[
        ~df["Категория"].str.lower().str.contains("|".join(income_keywords), na=False)
    ]

    expenses["weekday"] = expenses["Дата операции"].dt.day_name()

    grouped = (
        expenses.groupby("weekday", dropna=True)["Сумма платежа"].sum().reset_index()
    )

    result = []
    for _, row in grouped.iterrows():
        result.append(
            {
                "weekday": row["weekday"],
                "total_amount": round(float(row["Сумма платежа"]), 2),
            }
        )
    return result


def report_spending_by_workday_type(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"workday": 0.0, "weekend": 0.0}

    income_keywords = ["пополнение", "проценты", "кэшбэк"]
    expenses = df[
        ~df["Категория"].str.lower().str.contains("|".join(income_keywords), na=False)
    ]

    expenses["is_weekend"] = expenses["Дата операции"].dt.weekday.isin(
        [5, 6]
    )  # Сб и Вс

    total_work = expenses[~expenses["is_weekend"]]["Сумма платежа"].sum()
    total_weekend = expenses[expenses["is_weekend"]]["Сумма платежа"].sum()

    return {
        "workday": round(float(total_work), 2),
        "weekend": round(float(total_weekend), 2),
    }
