from pathlib import Path

from src.logger_config import logger_utils
from src.reports import (
    generate_cashback_json,
    generate_main_page_json,
    generate_report_spending_by_category_json,
    generate_report_spending_by_weekday_json,
    generate_report_spending_by_workday_type_json,
    generate_search_by_phone_json,
    generate_search_json,
    generate_transfers_to_individuals_json,
)


def main() -> None:
    logger_utils.info('Приложение запущено. Начало работы main().')

    client_id = 'CUST-998877'
    current_datetime_str = '2026-07-31 14:23:15'

    data_path = Path('data')
    transactions_file = str(data_path / 'transactions.xlsx')
    settings_file = str(data_path / 'user_settings.json')

    if not data_path.exists():

        logger_utils.error(
            f'Папка {str(data_path)} не найдена. Сначала запусти scripts/create_test_data.py'
        )
        return

    main_page = generate_main_page_json(
        current_datetime_str, transactions_file=transactions_file
    )
    print('\n=== Main Page ===')
    print(main_page)

    cashback = generate_cashback_json(
        client_id,
        currency='RUB',
        top_n=5,
        transactions_file=transactions_file,
        settings_file=settings_file,
    )
    print('\n=== Cashback ===')
    print(cashback)

    search = generate_search_json(
        'продукты', limit=5, transactions_file=transactions_file
    )
    print('\n=== Search ===')
    print(search)

    search_phone = generate_search_by_phone_json(
        '+79991234567', limit=10, transactions_file=transactions_file
    )
    print('\n=== Search by Phone ===')
    print(search_phone)

    transfers = generate_transfers_to_individuals_json(
        client_id, limit=3, transactions_file=transactions_file
    )
    print('\n=== Transfers to Individuals ===')
    print(transfers)

    by_category = generate_report_spending_by_category_json(
        client_id, days=30, transactions_file=transactions_file
    )
    print('\n=== Spending by Category ===')
    print(by_category)

    by_weekday = generate_report_spending_by_weekday_json(
        client_id, days=30, transactions_file=transactions_file
    )
    print('\n=== Spending by Weekday ===')
    print(by_weekday)

    by_workday = generate_report_spending_by_workday_type_json(
        client_id, days=30, transactions_file=transactions_file
    )
    print('\n=== Spending by Workday Type ===')
    print(by_workday)

    logger_utils.info('Приложение завершено. Все отчёты сгенерированы.')


if __name__ == '__main__':
    main()
