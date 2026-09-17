from datetime import datetime as real_datetime
from unittest.mock import patch

import pandas as pd
import pytest

from src.logger_config import logger_utils
from src.utils import get_greeting, load_transactions


class TestGetGreeting:
    @patch('src.utils.real_datetime')
    def test_get_greeting_morning(self, mock_dt):
        mock_dt.now.return_value = real_datetime(2026, 7, 31, 8, 30)
        assert get_greeting() == 'Доброе утро!'

    @patch('src.utils.real_datetime')
    def test_get_greeting_day(self, mock_dt):
        mock_dt.now.return_value = real_datetime(2026, 7, 31, 14, 15)
        assert get_greeting() == 'Добрый день!'

    @patch('src.utils.real_datetime')
    def test_get_greeting_evening(self, mock_dt):
        mock_dt.now.return_value = real_datetime(2026, 7, 31, 20, 5)
        assert get_greeting() == 'Добрый вечер!'

    @patch('src.utils.real_datetime')
    def test_get_greeting_night(self, mock_dt):
        mock_dt.now.return_value = real_datetime(2026, 7, 31, 2, 45)
        assert get_greeting() == 'Доброй ночи!'

    def test_get_greeting_custom_valid_time(self):
        assert get_greeting('2026-07-31 10:20:30') == 'Доброе утро!'
        assert get_greeting('2026-07-31 15:00:00') == 'Добрый день!'
        assert get_greeting('2026-07-31 21:10:00') == 'Добрый вечер!'
        assert get_greeting('2026-07-31 01:05:00') == 'Доброй ночи!'

    def test_get_greeting_invalid_format(self):
        with patch.object(logger_utils, 'warning') as mock_warn:
            result = get_greeting('неверная дата')
            mock_warn.assert_called_once()
            assert isinstance(result, str)


class TestLoadTransactions:
    @pytest.fixture
    def mock_path_exists(self):
        with patch('pathlib.Path.exists', return_value=True) as mock:
            yield mock

    @pytest.fixture
    def mock_read_excel(self):
        with patch('pandas.read_excel', return_value=pd.DataFrame()) as mock:
            yield mock

    @pytest.fixture
    def sample_df(self):
        return pd.DataFrame(
            {
                'Дата операции': ['2023-10-01', '2023-10-02'],
                'Сумма операции': [1200.0, 800.0],
                'Категория': ['Продукты', 'Такси'],
                'Описание': ['Пятёрочка', 'Яндекс Такси'],
                'Номер карты': ['4111111111111111', None],
            }
        )

    def test_load_transactions_success(
        self, mock_path_exists, mock_read_excel, sample_df
    ):
        sample_df['Дата операции'] = pd.to_datetime(sample_df['Дата операции'])
        mock_read_excel.return_value = sample_df
        path_str = 'test_file.xlsx'

        with patch.object(logger_utils, 'debug') as mock_debug, patch.object(
            logger_utils, 'info'
        ) as mock_info:
            result = load_transactions(path_str)

            assert isinstance(result, pd.DataFrame)
            assert 'last_digits' in result.columns
            assert len(result) == 2
            mock_debug.assert_called()
            mock_info.assert_any_call('Загружено строк: 2')
            mock_info.assert_any_call('Загрузка и обработка данных завершена')

    def test_load_transactions_file_not_found(self, mock_path_exists):
        mock_path_exists.return_value = False
        with patch.object(logger_utils, 'error') as mock_error:
            with pytest.raises(FileNotFoundError):
                load_transactions('nonexistent.xlsx')
            mock_error.assert_called_once()

    def test_load_transactions_sorting(
        self, mock_path_exists, mock_read_excel, sample_df
    ):
        sample_df['Дата операции'] = pd.to_datetime(sample_df['Дата операции'])
        mock_read_excel.return_value = sample_df

        result = load_transactions('test_file.xlsx')
        assert result['Дата операции'].iloc[0] > result['Дата операции'].iloc[-1]
