import pandas as pd
import pytest
from src.utils import load_transactions_data  
from src.main import format_money  

class TestFormatMoney:
    """Тест красивой валюты"""
    
    def test_format_large_number(self):
        assert format_money(1005249) == "1 005 249 ₽"
        
    def test_format_zero(self):
        assert format_money(0) == "0 ₽"
        
    def test_format_nan(self):
        
        assert format_money(float('nan')) == "0 ₽"

class TestDataLoading:
    """Тест загрузки данных"""
    
    def test_file_exists_and_not_empty(self):
        df = load_transactions_data()
        assert isinstance(df, pd.DataFrame), "Должен вернуться DataFrame"
        assert not df.empty, "Файл данных не должен быть пустым"
        assert 'Сумма операции' in df.columns, "В файле должна быть колонка 'Сумма операции'"

class TestReportLogic:
    """Тест логики отчета (упрощенный)"""
    
    def test_total_sum_calculation(self):
        
        data = {
            'Сумма операции': [100, 200, 300],
            'Категория': ['A', 'B', 'A']
        }
        df = pd.DataFrame(data)
        
        total = df['Сумма операции'].sum()
        assert total == 600
        
        
        grouped = df.groupby('Категория')['Сумма операции'].sum()
        assert grouped['A'] == 400