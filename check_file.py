import pandas as pd
from pathlib import Path


file_path = Path("data") / "operations.xlsx"

print(f"Проверяем файл: {file_path.absolute()}")

if not file_path.exists():
    print("❌ ФАЙЛ НЕ НАЙДЕН! Проверь название папки.")
else:
    try:
        df = pd.read_excel(file_path, engine="openpyxl")
        print(f"✅ Файл найден! В нём строк: {len(df)}")
        
        
        print("\n--- Первые 3 категории ---")
        print(df['Категория'].head(3).tolist())
        
        print("\n--- Последние 3 категории ---")
        print(df['Категория'].tail(3).tolist())
        
        
        if "ТЕСТ_ИЗ_ФАЙЛА" in df['Категория'].values:
            print("\n🎉 УРА! Твоя тестовая строка ЕСТЬ в файле!")
        else:
            print("\n😕 Твоей тестовой строки НЕТ в файле. Файл не обновился.")
            
    except Exception as e:
        print(f"❌ Ошибка при чтении: {e}")