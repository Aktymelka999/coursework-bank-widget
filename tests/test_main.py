
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

from src import main
from src.services import generate_events_page_json


def test_events_page_json():
    data = generate_events_page_json()
    assert isinstance(data, dict)
    assert 'greeting' in data
    assert 'timestamp' in data or 'generated_at' in data


class TestMain:
    @pytest.fixture
    def temp_data_dir(self, tmp_path: Path):
        """Создаёт временную папку data со структурой как в задании."""
        data_dir = tmp_path / 'data'
        data_dir.mkdir()

        (data_dir / 'transactions.xlsx').touch()
        (data_dir / 'user_settings.json').touch()


        yield data_dir

        if data_dir.exists():
            shutil.rmtree(data_dir)

    @patch('src.main.generate_main_page_json')
    @patch('src.main.generate_cashback_json')
    @patch('src.main.generate_search_json')
    @patch('src.main.generate_search_by_phone_json')
    @patch('src.main.generate_transfers_to_individuals_json')
    @patch('src.main.generate_report_spending_by_category_json')
    @patch('src.main.generate_report_spending_by_weekday_json')
    @patch('src.main.generate_report_spending_by_workday_type_json')
    def test_main_flow_success(
        self,
        mock_workday_type,
        mock_weekday,
        mock_by_category,
        mock_transfers,
        mock_search_phone,
        mock_search,
        mock_cashback,
        mock_main_page,
        temp_data_dir: Path,
    ):

        import os
        original_cwd = os.getcwd()

        try:
            os.chdir(temp_data_dir.parent)  # Теперь Path("data") == temp_data_dir

            # Заглушки для генераторов
            mock_main_page.return_value = {'page': 'main', 'data': []}
            mock_cashback.return_value = {'cashback': []}
            mock_search.return_value = {'results': []}
            mock_search_phone.return_value = {'results': []}
            mock_transfers.return_value = {'transfers': []}
            mock_by_category.return_value = {'report': []}
            mock_weekday.return_value = {'by_weekday': []}
            mock_workday_type.return_value = {'by_workday_type': []}

            main.main()

            assert mock_main_page.called is True
            assert mock_cashback.called is True

        finally:
            os.chdir(original_cwd)

    def test_main_data_folder_missing(self, tmp_path: Path):
        """
        Проверяем ветку, когда папки data нет.
        Мы просто не создаём папку data в tmp_path.
        """
        import os
        original_cwd = os.getcwd()

        try:

            os.chdir(tmp_path)

            with patch.object(main.logger_utils, 'error') as mock_logger_error:
                main.main()


                assert mock_logger_error.call_count == 1


                log_message = mock_logger_error.call_args[0][0]

                assert 'Папка data не найдена' in log_message
        finally:
            os.chdir(original_cwd)
