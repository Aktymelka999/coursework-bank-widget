from unittest.mock import patch

from src.masks import mask_card_number


class TestMasks:
    @patch('src.masks.logger_masks')
    def test_mask_card_number_valid(self, mock_logger):
        result = mask_card_number('4111111111111111')
        assert result == '4111********1111'

        mock_logger.debug.assert_called_once()
        mock_logger.info.assert_called_once()
        mock_logger.warning.assert_not_called()
        mock_logger.error.assert_not_called()

    @patch('src.masks.logger_masks')
    def test_mask_card_number_with_separators(self, mock_logger):
        # Дефисы и пробелы должны удаляться до маскирования
        result = mask_card_number('4111-1111-1111-1111')
        assert result == '4111********1111'

        result2 = mask_card_number('4111 1111 1111 1111')
        assert result2 == '4111********1111'

        mock_logger.debug.assert_called()
        mock_logger.info.assert_called()
        mock_logger.warning.assert_not_called()
        mock_logger.error.assert_not_called()

    @patch('src.masks.logger_masks')
    def test_mask_card_number_short_input(self, mock_logger):
        # Короткий номер — возвращается как есть, плюс warning
        result = mask_card_number('1234')
        assert result == '1234'

        mock_logger.debug.assert_called_once()
        mock_logger.warning.assert_called_once()
        mock_logger.info.assert_not_called()
        mock_logger.error.assert_not_called()

    @patch('src.masks.logger_masks')
    def test_mask_card_number_non_string(self, mock_logger):
        # Не строка — ошибка и возврат "****"
        result = mask_card_number(12345)
        assert result == '****'

        mock_logger.debug.assert_called_once()
        mock_logger.error.assert_called_once()
        mock_logger.warning.assert_not_called()
        mock_logger.info.assert_not_called()

    @patch('src.masks.logger_masks')
    def test_mask_card_number_empty_string(self, mock_logger):
        result = mask_card_number('')
        assert result == ''

        mock_logger.debug.assert_called_once()
        mock_logger.warning.assert_called_once()  # len < 8
        mock_logger.info.assert_not_called()
        mock_logger.error.assert_not_called()
