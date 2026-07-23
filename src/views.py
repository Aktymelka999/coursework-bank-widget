import datetime
import pandas as pd


def generate_main_page_json(df):
    now = datetime.datetime.now()
    hour = now.hour

    if 6 <= hour <= 11:
        greeting = "Доброе утро"
    elif 12 <= hour <= 17:
        greeting = "Добрый день"
    elif 18 <= hour <= 22:
        greeting = "Добрый вечер"
    else:
        greeting = "Доброй ночи"

    cards = [
        {
            "card_id": "123456",
            "last_four": "4201",
            "brand": "Mastercard",
            "balance": 15000.0,
            "currency": "RUB",
        }
    ]

    sorted_df = df.sort_values(by="Сумма операции", ascending=False)
    top_5 = sorted_df.head(5)

    top_transactions = []
    for _, row in top_5.iterrows():
        dt = row["Дата операции"]

        if isinstance(dt, pd.Timestamp):
            date_str = dt.strftime("%d.%m.%Y")
        elif isinstance(dt, datetime.date):
            date_str = dt.strftime("%d.%m.%Y")
        else:

            date_str = str(dt)

        top_transactions.append(
            {
                "date": date_str,
                "amount": int(row["Сумма операции"]),
                "category": row["Категория"],
                "description": row.get("Описание", "Без описания"),
            }
        )

    currency_rates = [
        {"currency": "USD", "rate": 90.5},
        {"currency": "EUR", "rate": 100.2},
        {"currency": "CNY", "rate": 12.5},
    ]

    stock_prices = [
        {"stock": "YNDX", "price": 3500.0},
        {"stock": "SBER", "price": 280.0},
        {"stock": "GAZP", "price": 160.0},
    ]

    return {
        "greeting": greeting,
        "cards": cards,
        "top_transactions": top_transactions,
        "currency_rates": currency_rates,
        "stock_prices": stock_prices,
    }


def generate_report_spending_by_category_json(df, top_n=7):
    grouped = (
        df.groupby("Категория")["Сумма операции"].sum().sort_values(ascending=False)
    )

    top = grouped.head(top_n)
    rest = grouped[top_n:].sum()

    result = []
    for cat, amt in top.items():
        result.append({"category": cat, "amount": int(amt)})

    if rest > 0:
        result.append({"category": "Остальное", "amount": int(rest)})

    return {"data": result}


def generate_events_page_json(df, date_str, range_type="M"):
    total_expenses = df["Сумма операции"].sum()
    return {
        "expenses": {"total_amount": int(total_expenses)},
        "period": date_str,
        "range_type": range_type,
    }


def generate_investment_bank_json(initial_amount, percent):
    investment_amount = initial_amount * (percent / 100)
    return {
        "initial_amount": initial_amount,
        "percent": percent,
        "investment_amount": int(investment_amount),
    }


def generate_search_json(df, query):
    query_lower = query.lower()
    mask = df["Описание"].astype(str).str.lower().str.contains(query_lower, na=False)
    found = df[mask]
    return {
        "query": query,
        "count": len(found),
        "results": found.to_dict(orient="records"),
    }


def generate_cashback_json():
    cashback_categories = [
        {"category": "Продукты", "cashback_percent": 5.0},
        {"category": "Такси", "cashback_percent": 7.0},
        {"category": "Электроника", "cashback_percent": 3.0},
        {"category": "Рестораны", "cashback_percent": 6.0},
    ]
    return {"categories": cashback_categories}


def generate_search_by_phone_json(df, fragment):
    col_to_search = "Телефон" if "Телефон" in df.columns else "Описание"
    mask = df[col_to_search].astype(str).str.contains(fragment, na=False, case=False)
    found = df[mask]
    return {"fragment": fragment, "count": len(found)}


def generate_transfers_to_individuals_json(df):
    transfers = df[df["Категория"].astype(str).str.lower() == "переводы"]
    return {
        "count": len(transfers),
        "total_amount": (
            int(transfers["Сумма операции"].sum()) if not transfers.empty else 0
        ),
    }


def generate_report_spending_by_weekday_json(df):
    if "Дата операции" not in df.columns:
        return {"data": []}

    df = df.copy()

    df["date_ts"] = pd.to_datetime(df["Дата операции"], errors="coerce")
    df["weekday"] = df["date_ts"].dt.day_name()
    grouped = df.groupby("weekday")["Сумма операции"].sum()

    result = []
    for day, amt in grouped.items():
        result.append({"weekday": day, "total_amount": int(amt)})
    return {"data": result}


def generate_report_spending_by_workday_type_json(df):
    if "Дата операции" not in df.columns:
        return {"data": {"workday": 0, "weekend": 0}}

    df = df.copy()
    df["date_ts"] = pd.to_datetime(df["Дата операции"], errors="coerce")
    df["is_weekend"] = df["date_ts"].dt.weekday >= 5

    weekend_sum = df[df["is_weekend"]]["Сумма операции"].sum()
    workday_sum = df[~df["is_weekend"]]["Сумма операции"].sum()

    return {"data": {"workday": int(workday_sum), "weekend": int(weekend_sum)}}
