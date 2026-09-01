import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import numpy as np

from .logger_config import logger_utils


# -----------------------------------------------------------------------------
# Вспомогательные функции
# -----------------------------------------------------------------------------

def _load_user_settings(settings_path: str) -> Dict[str, Any]:
    path = Path(settings_path)
    if not path.exists():
        logger_utils.warning(f"Файл настроек не найден: {settings_path}. Используем дефолтные.")
        return {"user_currencies": ["RUB"], "user_stocks": []}

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return dict(data)
    except Exception as e:
        logger_utils.error(f"Ошибка чтения user_settings.json: {e}")
        return {"user_currencies": ["RUB"], "user_stocks": []}


def _load_transactions_from_excel(file_path: str) -> pd.DataFrame:
    path = Path(file_path)
    logger_utils.debug(f"Загрузка транзакций из {path}")

    if not path.exists():
        logger_utils.error(f"Файл транзакций не найден: {path}")
        return pd.DataFrame()

    try:
        df = pd.read_excel(path, engine="openpyxl")
        logger_utils.info(f"Загружено строк транзакций: {len(df)}")

        rename_map = {
            "Дата операции": "date",
            "Дата": "date",
            "Date": "date",
            "Сумма операции": "amount",
            "Сумма": "amount",
            "Amount": "amount",
            "Валюта": "currency",
            "Currency": "currency",
            "Категория": "category",
            "Category": "category",
            "ID транзакции": "transaction_id",
            "Transaction ID": "transaction_id",
            "Телефон": "phone",
            "Phone": "phone",
            "Тип перевода": "transfer_type",
            "Transfer Type": "transfer_type",
            "Описание": "description",
            "Description": "description",
        }
        existing_cols = {k: v for k, v in rename_map.items() if k in df.columns}
        df = df.rename(columns=existing_cols)

        if "amount" not in df.columns:
            logger_utils.warning('Нет колонки "amount". Не сможем считать кешбэк и траты.')
        if "currency" not in df.columns:
            df["currency"] = "RUB"
        if "category" not in df.columns:
            df["category"] = "Прочее"

        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
        if "amount" in df.columns:
            df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)

        return df
    except Exception as e:
        logger_utils.error(f"Ошибка чтения Excel: {e}")
        return pd.DataFrame()


# -----------------------------------------------------------------------------
# Отчёты
# -----------------------------------------------------------------------------

WEEKDAYS_ORDER = [
    "Понедельник",
    "Вторник",
    "Среда",
    "Четверг",
    "Пятница",
    "Суббота",
    "Воскресенье",
]


def _weekday_name(idx: int) -> str:
    return WEEKDAYS_ORDER[idx]


def generate_cashback_json(
    client_id: str,
    currency: str = "RUB",
    top_n: int = 5,
    settings_file: str = "data/user_settings.json",
    transactions_file: str = "data/transactions.xlsx",
) -> Dict[str, Any]:
    logger_utils.debug(
        "generate_cashback_json called",
        extra={"client_id": client_id, "currency": currency, "top_n": top_n},
    )

    settings = _load_user_settings(settings_file)
    user_currencies = settings.get("user_currencies", ["RUB"])
    if currency not in user_currencies:
        user_currencies.append(currency)

    df = _load_transactions_from_excel(transactions_file)

    if df.empty:
        logger_utils.warning("Транзакции не загружены. Возвращаем пустой отчёт.")
        return {
            "report_type": "cashback_summary",
            "client_id": client_id,
            "currency": currency,
            "generated_at": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
            "cashback": {"total": 0.0, "top_categories": [], "transactions": []},
            "settings_used": {
                "user_currencies_in_profile": user_currencies,
                "requested_currency": currency,
                "source": "no_data",
            },
        }

    filtered = df[df["currency"] == currency].copy()
    if filtered.empty:
        filtered = df.copy()
        logger_utils.warning(
            f"Нет транзакций в валюте {currency}. Используем смешанные валюты."
        )

    cashback_rates = {
        "Супермаркеты": 0.05,
        "Рестораны": 0.10,
        "Такси": 0.03,
        "Электроника": 0.02,
        "АЗС": 0.04,
        "Аптеки": 0.07,
        "Одежда": 0.06,
        "Развлечения": 0.08,
    }

    def calc_cashback(row: pd.Series) -> float:
        rate = cashback_rates.get(row["category"], 0.01)
        amount = row["amount"]
        if amount < 0:
            return float(abs(amount) * rate)
        return 0.0

    filtered["cashback"] = filtered.apply(calc_cashback, axis=1)
    total_cashback = round(filtered["cashback"].sum(), 2)

    top_transactions = filtered.sort_values(by="cashback", ascending=False).head(top_n)
    result_transactions = top_transactions.to_dict(orient="records")

    top_categories_df = (
        filtered.groupby("category")["cashback"]
        .sum()
        .sort_values(ascending=False)
        .head(5)
        .reset_index()
    )
    top_categories = [
        {"category": row["category"], "amount": round(row["cashback"], 2)}
        for _, row in top_categories_df.iterrows()
    ]

    return {
        "report_type": "cashback_summary",
        "client_id": client_id,
        "currency": currency,
        "generated_at": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        "cashback": {
            "total": total_cashback,
            "top_categories": top_categories,
            "transactions": result_transactions,
        },
        "settings_used": {
            "user_currencies_in_profile": user_currencies,
            "requested_currency": currency,
            "source": "transactions.xlsx",
        },
    }


def generate_main_page_json(
    date_time_str: Optional[str] = None,
    transactions_file: str = "data/transactions.xlsx",
) -> Dict[str, Any]:
    logger_utils.debug(
        "generate_main_page_json called",
        extra={"date_time": date_time_str},
    )
    logger_utils.info("Генерация главной страницы на основе данных из файла")

    try:
        base_date = (
            pd.to_datetime(date_time_str) if date_time_str else pd.Timestamp.now()
        )
    except Exception:
        base_date = pd.Timestamp.now()
        logger_utils.warning(
            "Неверный формат даты для главной страницы, используем текущее время"
        )

    hour = base_date.hour
    greeting = "Доброе утро!"
    if 12 <= hour < 18:
        greeting = "Добрый день!"
    elif 18 <= hour < 23:
        greeting = "Добрый вечер!"
    else:
        greeting = "Доброй ночи!"

    df = _load_transactions_from_excel(transactions_file)

    if df.empty:
        logger_utils.warning(
            "Файл транзакций пуст или не загружен. Возвращаем нулевые значения."
        )
        total_balance = 0.0
        pending_operations = 0
        recent_transactions: List[Dict[str, Any]] = []
    else:
        total_balance = round(df["amount"].sum(), 2)
        pending_operations = 0

        recent_transactions = []
        if "date" in df.columns and not df["date"].isna().all():
            df_sorted = df.sort_values(by="date", ascending=False)
            recent_df = df_sorted.head(3)
            for _, row in recent_df.iterrows():
                trans = {
                    "id": str(row.get("transaction_id", "UNKNOWN")),
                    "date": (
                        row["date"].strftime("%Y-%m-%d")
                        if pd.notna(row.get("date"))
                        else "Unknown"
                    ),
                    "category": str(row.get("category", "Прочее")),
                    "amount": round(row["amount"], 2),
                    "currency": str(row.get("currency", "RUB")),
                }
                recent_transactions.append(trans)

    return {
        "report_type": "main_page",
        "greeting": greeting,
        "generated_at": base_date.strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "total_balance": total_balance,
            "currency": "RUB",
            "pending_operations": pending_operations,
        },
        "recent_transactions": recent_transactions,
    }


def generate_search_json(
    query: str,
    limit: int = 10,
    transactions_file: str = "data/transactions.xlsx",
) -> Dict[str, Any]:
    logger_utils.debug(
        "generate_search_json called",
        extra={"query": query, "limit": limit},
    )
    logger_utils.info(f'Поиск по запросу "{query}"')

    df = _load_transactions_from_excel(transactions_file)

    if df.empty:
        logger_utils.warning("Файл транзакций пуст. Поиск не дал результатов.")
        return {
            "report_type": "search_results",
            "query": query,
            "limit": limit,
            "results": [],
        }

    mask = pd.Series([False] * len(df))
    if "description" in df.columns:
        mask |= df["description"].astype(str).str.contains(query, case=False, na=False)
    if "category" in df.columns:
        mask |= df["category"].astype(str).str.contains(query, case=False, na=False)

    found = df[mask].head(limit)

    results = []
    for _, row in found.iterrows():
        results.append(
            {
                "id": str(row.get("transaction_id", "UNKNOWN")),
                "date": (
                    row["date"].strftime("%Y-%m-%d")
                    if "date" in row and pd.notna(row["date"])
                    else "Unknown"
                ),
                "category": str(row.get("category", "Прочее")),
                "description": str(row.get("description", "")),
                "amount": round(row["amount"], 2),
                "currency": str(row.get("currency", "RUB")),
            }
        )

    return {
        "report_type": "search_results",
        "query": query,
        "limit": limit,
        "results": results,
    }


def generate_search_by_phone_json(
    phone: str,
    limit: int = 10,
    transactions_file: str = "data/transactions.xlsx",
) -> dict:
    logger_utils.info(f"Поиск транзакций по телефону: {phone}, лимит: {limit}")

    df = _load_transactions_from_excel(transactions_file)

    if df.empty:
        logger_utils.warning("Нет транзакций для поиска.")
        return {
            "report_type": "search_by_phone",
            "query": phone,
            "limit": limit,
            "results": [],
        }

    if "phone" not in df.columns:
        logger_utils.error('Колонка "phone" не найдена в файле транзакций.')
        return {
            "report_type": "search_by_phone",
            "query": phone,
            "limit": limit,
            "results": [],
        }

    clean_query = "".join(filter(str.isdigit, str(phone)))

    if not clean_query:
        logger_utils.warning("В запросе не найдено цифр для поиска телефона.")
        return {
            "report_type": "search_by_phone",
            "query": phone,
            "limit": limit,
            "results": [],
        }

    df["_phone_normalized"] = df["phone"].astype(str).str.replace(r"\D", "", regex=True)

    mask = df["_phone_normalized"] == clean_query
    filtered = df[mask].copy()

    if "_phone_normalized" in filtered.columns:
        del filtered["_phone_normalized"]

    results = []
    for _, row in filtered.head(limit).iterrows():
        results.append(
            {
                "id": row.get("id"),
                "date": str(row.get("date", "")),
                "category": row.get("category"),
                "description": row.get("description", ""),
                "amount": row.get("amount"),
                "currency": row.get("currency"),
                "phone": row.get("phone"),
            }
        )

    return {
        "report_type": "search_by_phone",
        "query": phone,
        "limit": limit,
        "results": results,
    }


def generate_transfers_to_individuals_json(
    client_id: str,
    limit: int = 10,
    transactions_file: str = "data/transactions.xlsx",
) -> Dict[str, Any]:
    logger_utils.debug(
        "generate_transfers_to_individuals_json called",
        extra={"client_id": client_id, "limit": limit},
    )
    logger_utils.info(f"Генерация переводов физлицам для клиента {client_id}")

    df = _load_transactions_from_excel(transactions_file)

    if df.empty:
        logger_utils.warning("Файл транзакций пуст. Переводов не найдено.")
        return {
            "report_type": "transfers_to_individuals",
            "client_id": client_id,
            "transfers": [],
        }

    is_transfer_mask = pd.Series([False] * len(df))

    if "category" in df.columns:
        is_transfer_mask |= df["category"].str.lower().str.contains("перевод", na=False)

    if "transfer_type" in df.columns:
        is_transfer_mask |= df["transfer_type"].str.lower() == "individual"

    transfers_df = df[is_transfer_mask].head(limit)

    transfers = []
    if not transfers_df.empty:
        for _, row in transfers_df.iterrows():
            transfers.append(
                {
                    "id": str(row.get("transaction_id", "UNKNOWN")),
                    "date": (
                        row["date"].strftime("%Y-%m-%d")
                        if "date" in row and pd.notna(row["date"])
                        else "Unknown"
                    ),
                    "category": str(row.get("category", "Прочее")),
                    "description": str(row.get("description", "")),
                    "amount": round(row["amount"], 2),
                    "currency": str(row.get("currency", "RUB")),
                    "recipient": str(row.get("recipient", "Не указано")),
                    "phone": str(row.get("phone", "")),
                    "transfer_type": str(row.get("transfer_type", "")),
                }
            )

    return {
        "report_type": "transfers_to_individuals",
        "client_id": client_id,
        "limit": limit,
        "transfers": transfers,
    }


def generate_report_spending_by_category_json(
    client_id: str,
    days: int = 30,
    reference_date: Optional[pd.Timestamp] = None,
    transactions_file: str = "data/transactions.xlsx",
) -> Dict[str, Any]:
    logger_utils.debug(
        "generate_report_spending_by_category_json called",
        extra={"client_id": client_id, "days": days},
    )

    df = _load_transactions_from_excel(transactions_file)

    if df.empty:
        logger_utils.warning("Нет транзакций для отчёта по категориям.")
        return {
            "report_type": "spending_by_category",
            "client_id": client_id,
            "by_category": [],
            "total": 0.0,
            "period": {
                "days": days,
                "reference_date": str(reference_date or pd.Timestamp.now()),
            },
        }

    if "date" not in df.columns or "amount" not in df.columns:
        logger_utils.error('Для отчёта по категориям требуются колонки "date" и "amount".')
        return {
            "report_type": "spending_by_category",
            "client_id": client_id,
            "by_category": [],
            "total": 0.0,
            "period": {
                "days": days,
                "reference_date": str(reference_date or pd.Timestamp.now()),
            },
        }

    if reference_date is None:
        reference_date = df["date"].max()

    start_date = reference_date - pd.Timedelta(days=days)
    period_df = df[(df["date"] >= start_date) & (df["date"] <= reference_date)].copy()

    if period_df.empty:
        logger_utils.info("В заданном периоде нет транзакций.")
        return {
            "report_type": "spending_by_category",
            "client_id": client_id,
            "by_category": [],
            "total": 0.0,
            "period": {
                "days": days,
                "reference_date": str(reference_date),
            },
        }

    spending = period_df[period_df["amount"] < 0].copy()

    if spending.empty:
        return {
            "report_type": "spending_by_category",
            "client_id": client_id,
            "by_category": [],
            "total": 0.0,
            "period": {
                "days": days,
                "reference_date": str(reference_date),
            },
        }

    grouped = (
        spending.groupby("category")["amount"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )
    grouped.rename(columns={"amount": "total_amount"}, inplace=True)

    result_rows = [
        {
            "category": row["category"],
            "total_amount": round(row["total_amount"], 2),
        }
        for _, row in grouped.iterrows()
    ]

    total = round(grouped["total_amount"].sum(), 2)

    return {
        "report_type": "spending_by_category",
        "client_id": client_id,
        "by_category": result_rows,
        "total": total,
        "period": {
            "days": days,
            "reference_date": reference_date.isoformat(),
            "start_date": start_date.isoformat(),
        },
    }


def generate_report_spending_by_weekday_json(
    client_id: str,
    days: int = 7,
    reference_date: Optional[pd.Timestamp] = None,
    transactions_file: str = "data/transactions.xlsx",
) -> dict:
    logger_utils.debug(
        "generate_report_spending_by_weekday_json called",
        extra={"client_id": client_id, "days": days},
    )

    df = _load_transactions_from_excel(transactions_file)

    if df.empty:
        return {
            "report_type": "spending_by_weekday",
            "client_id": client_id,
            "by_weekday": [
                {"weekday_index": i, "weekday_name": _weekday_name(i), "amount": 0.0}
                for i in range(7)
            ],
            "total": 0.0,
            "period": {
                "days": days,
                "reference_date": (reference_date or pd.Timestamp.now()).isoformat(),
                "start_date": ((reference_date or pd.Timestamp.now()) - pd.Timedelta(days=days)).isoformat(),
            },
        }

    if "date" not in df.columns or "amount" not in df.columns:
        logger_utils.error('Для отчёта требуются колонки "date" и "amount".')
        return {
            "report_type": "spending_by_weekday",
            "client_id": client_id,
            "by_weekday": [
                {"weekday_index": i, "weekday_name": _weekday_name(i), "amount": 0.0}
                for i in range(7)
            ],
            "total": 0.0,
            "period": {
                "days": days,
                "reference_date": (reference_date or pd.Timestamp.now()).isoformat(),
                "start_date": ((reference_date or pd.Timestamp.now()) - pd.Timedelta(days=days)).isoformat(),
            },
        }

    if reference_date is None:
        reference_date = df["date"].max()

    start_date = reference_date - pd.Timedelta(days=days)
    period_df = df[(df["date"] >= start_date) & (df["date"] <= reference_date)].copy()

    if period_df.empty:
        return {
            "report_type": "spending_by_weekday",
            "client_id": client_id,
            "by_weekday": [
                {"weekday_index": i, "weekday_name": _weekday_name(i), "amount": 0.0}
                for i in range(7)
            ],
            "total": 0.0,
            "period": {
                "days": days,
                "reference_date": reference_date.isoformat(),
                "start_date": start_date.isoformat(),
            },
        }

    spending = period_df[period_df["amount"] < 0].copy()

    if spending.empty:
        return {
            "report_type": "spending_by_weekday",
            "client_id": client_id,
            "by_weekday": [
                {"weekday_index": i, "weekday_name": _weekday_name(i), "amount": 0.0}
                for i in range(7)
            ],
            "total": 0.0,
            "period": {
                "days": days,
                "reference_date": reference_date.isoformat(),
                "start_date": start_date.isoformat(),
            },
        }

    spending["weekday"] = spending["date"].dt.dayofweek
    agg = (
        spending.groupby("weekday")["amount"]
        .sum()
        .reindex(range(7), fill_value=0)
    )

    result_list = [
        {
            "weekday_index": idx,
            "weekday_name": _weekday_name(idx),
            "amount": float(val),
        }
        for idx, val in agg.items()
    ]

    total = float(agg.sum())

    return {
        "report_type": "spending_by_weekday",
        "client_id": client_id,
        "by_weekday": result_list,
        "total": total,
        "period": {
            "days": days,
            "reference_date": reference_date.isoformat(),
            "start_date": start_date.isoformat(),
        },
    }


def generate_report_spending_by_workday_type_json(
    client_id: str,
    days: int = 30,
    reference_date: Optional[pd.Timestamp] = None,
    transactions_file: str = "data/transactions.xlsx",
) -> Dict[str, Any]:
    logger_utils.debug(
        "generate_report_spending_by_workday_type_json called",
        extra={"client_id": client_id, "days": days},
    )

    df = _load_transactions_from_excel(transactions_file)

    if df.empty:
        return {
            "report_type": "spending_by_workday_type",
            "client_id": client_id,
            "by_workday_type": [
                {"workday_type": "Будни", "amount": 0.0},
                {"workday_type": "Выходные", "amount": 0.0},
            ],
            "total": 0.0,
            "period": {
                "days": days,
                "reference_date": (reference_date or pd.Timestamp.now()).isoformat(),
                "start_date": ((reference_date or pd.Timestamp.now()) - pd.Timedelta(days=days)).isoformat(),
            },
        }

    if "amount" not in df.columns or "date" not in df.columns:
        logger_utils.error('Отчёт требует колонок "amount" и "date".')
        return {
            "report_type": "spending_by_workday_type",
            "client_id": client_id,
            "by_workday_type": [
                {"workday_type": "Будни", "amount": 0.0},
                {"workday_type": "Выходные", "amount": 0.0},
            ],
            "total": 0.0,
            "period": {
                "days": days,
                "reference_date": (reference_date or pd.Timestamp.now()).isoformat(),
                "start_date": ((reference_date or pd.Timestamp.now()) - pd.Timedelta(days=days)).isoformat(),
            },
        }

    if reference_date is None:
        reference_date = df["date"].max()

    start_date = reference_date - pd.Timedelta(days=days)
    period_df = df[(df["date"] >= start_date) & (df["date"] <= reference_date)].copy()

    if period_df.empty:
        return {
            "report_type": "spending_by_workday_type",
            "client_id": client_id,
            "by_workday_type": [
                {"workday_type": "Будни", "amount": 0.0},
                {"workday_type": "Выходные", "amount": 0.0},
            ],
            "total": 0.0,
            "period": {
                "days": days,
                "reference_date": reference_date.isoformat(),
                "start_date": start_date.isoformat(),
            },
        }

    spending = period_df[period_df["amount"] < 0].copy()

    if spending.empty:
        return {
            "report_type": "spending_by_workday_type",
            "client_id": client_id,
            "by_workday_type": [
                {"workday_type": "Будни", "amount": 0.0},
                {"workday_type": "Выходные", "amount": 0.0},
            ],
            "total": 0.0,
            "period": {
                "days": days,
                "reference_date": reference_date.isoformat(),
                "start_date": start_date.isoformat(),
            },
        }

    spending["workday_type"] = spending["date"].dt.dayofweek.apply(
        lambda x: "Будни" if x < 5 else "Выходные"
    )

    grouped = (
        spending.groupby("workday_type")["amount"]
        .sum()
        .reindex(["Будни", "Выходные"], fill_value=0.0)
        .reset_index()
    )

    result_rows = [
        {"workday_type": row["workday_type"], "amount": round(row["amount"], 2)}
        for _, row in grouped.iterrows()
    ]

    total = round(grouped["amount"].sum(), 2)

    return {
        "report_type": "spending_by_workday_type",
        "client_id": client_id,
        "by_workday_type": result_rows,
        "total": total,
        "period": {
            "days": days,
            "reference_date": reference_date.isoformat(),
            "start_date": start_date.isoformat(),
        },
    }
