import os
import sys
import pandas as pd

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.utils import load_transactions_data
from src.views import (
    generate_main_page_json,
    generate_events_page_json,
    generate_investment_bank_json,
    generate_search_json,
    generate_cashback_json,
    generate_search_by_phone_json,
    generate_transfers_to_individuals_json,
    generate_report_spending_by_category_json,
    generate_report_spending_by_weekday_json,
    generate_report_spending_by_workday_type_json,
)


def format_money(amount) -> str:
    if pd.isna(amount) or amount == 0:
        return "0 ₽"
    return f"{amount:,.0f}".replace(",", " ") + " ₽"


def print_report(df, total_spent, avg_check, top_categories) -> None:
    print("\n" + "=" * 50)
    print("📊 ФИНАЛЬНЫЙ ОТЧЁТ ПО ТРАТАМ (для презентации)")
    print("=" * 50)

    min_date = None
    max_date = None

    if "Дата операции" in df.columns and not df.empty:
        dates = pd.to_datetime(df["Дата операции"], errors="coerce")
        min_dt = dates.min()
        max_dt = dates.max()

        if pd.notna(min_dt) and pd.notna(max_dt):
            min_date = min_dt.strftime("%Y-%m-%d")
            max_date = max_dt.strftime("%Y-%m-%d")

    if min_date and max_date:
        print(f"📅 Период анализа: {min_date} — {max_date}")
    else:
        print("📅 Период анализа: данные о датах недоступны")

    print(f"💳 Всего транзакций: {len(df)}")
    print(f"💰 Общая сумма расходов: {format_money(total_spent)}")
    print(f"📉 Средний чек: {format_money(avg_check)}")
    print("-" * 50)
    print("🔥 ТОП-3 категории по расходам:")

    if top_categories.empty:
        print("   Нет данных для отображения категорий.")
    else:
        for i, (category, amount) in enumerate(top_categories.items(), 1):
            print(f"   {i}. {category}: {format_money(amount)}")

    print("=" * 50 + "\n")


def main() -> None:
    print("=== КУРС 1: ПОЛНЫЙ ПРОГОН ВСЕХ ЭКРАНОВ И ОТЧЁТОВ ===\n")

    try:
        df = load_transactions_data()

        if df.empty:
            print("⚠️ Предупреждение: Загруженный файл данных пуст!")
            return

        print("--- Главная страница ---")
        main_json = generate_main_page_json(df)
        print(f"Приветствие: {main_json['greeting']}!")
        print(
            f"Карт: {len(main_json['cards'])}, Топ транзакций: {len(main_json['top_transactions'])}\n"
        )

        print("--- События (M) ---")
        events_json = generate_events_page_json(df, "2023-10-15", range_type="M")
        print(
            f"Расходы (всего): {format_money(events_json['expenses']['total_amount'])}\n"
        )

        print("--- Инвесткопилка ---")
        invest_json = generate_investment_bank_json(1051, 50)
        print(f"В копилку: {format_money(invest_json['investment_amount'])}\n")

        print("--- Простой поиск ('пятёрочка') ---")
        search_json = generate_search_json(df, "пятёрочка")
        print(f"Найдено: {search_json['count']}\n")

        print("--- Выгодные категории кешбэка ---")
        cb_json = generate_cashback_json()
        for c in cb_json["categories"]:
            print(f"- {c['category']}: {c['cashback_percent']}%")
        print()

        print("--- Поиск по телефону ('яндекс') ---")
        phone_json = generate_search_by_phone_json(df, "яндекс")
        print(f"Найдено по телефону/фрагменту: {phone_json['count']}\n")

        print("--- Переводы физлицам ---")
        trans_json = generate_transfers_to_individuals_json(df)
        print(f"Переводов физлицам: {trans_json['count']}\n")

        print("--- Отчёт: траты по категории ---")
        rep_cat_json = generate_report_spending_by_category_json(df, top_n=7)
        for r in rep_cat_json["data"]:
            print(f"- {r['category']}: {format_money(r['amount'])}")
        print()

        print("--- Отчёт: траты по дням недели ---")
        rep_wd_json = generate_report_spending_by_weekday_json(df)
        for r in rep_wd_json["data"]:
            print(f"- {r['weekday']}: {format_money(r['total_amount'])}")
        print()

        print("--- Отчёт: рабочий vs выходной ---")
        rep_type_json = generate_report_spending_by_workday_type_json(df)
        data = rep_type_json["data"]
        print(f"Рабочий день: {format_money(data['workday'])}")
        print(f"Выходной день: {format_money(data['weekend'])}\n")

        total_spent = df["Сумма операции"].sum()

        count_transactions = len(df)
        if count_transactions > 0:
            avg_check = df["Сумма операции"].mean()
        else:
            avg_check = 0

        top_categories = (
            df.groupby("Категория")["Сумма операции"]
            .sum()
            .sort_values(ascending=False)
            .head(3)
        )

        print_report(df, total_spent, avg_check, top_categories)

    except FileNotFoundError as e:
        print(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА: Файл с данными не найден!\n{e}")
        print("📁 Проверь, лежит ли файл operations.xlsx в папке data.")

    except Exception as e:
        print(f"\n❌ Произошла непредвиденная ошибка: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
